import json
from unittest.mock import MagicMock

import pytest

from backend.app.application.review_service import ReviewService
from backend.app.config import Settings
from backend.app.domain.document import BoundingBox, DocumentLayout, PageLayout, PageSource, TableRegion
from backend.app.domain.errors import ConflictError
from backend.app.infrastructure.database.models import Observation
from backend.app.infrastructure.ocr import OcrCancellationRequested
from backend.app.infrastructure.ollama import OllamaExtractor
from backend.app.infrastructure.ollama_verification import verify_fields


def document():
    table = TableRegion(1, BoundingBox(10, 20, 300, 100), (
        ("Coil", "C 10^-4", "Width mm"), ("A", "13", "900"), ("B", "20", "800")))
    return DocumentLayout("test.pdf", "hash", (PageLayout(1, 600, 800, 0, PageSource.DIGITAL, tables=(table,)),))


def certificate(current=.13):
    return {"products": [{"product_id": "A", "heat_no": "H1", "composition_pct": {"C": current},
        "observations": {"composition_pct": {"C": {"raw_value": "13", "normalized_value": current,
            "page_number": 1}}}}]}


def client(comparisons):
    assistant = OllamaExtractor(Settings(_env_file=None))
    assistant.opener = MagicMock()
    assistant.opener.open.return_value.__enter__.return_value.read.return_value = json.dumps({
        "done": True, "message": {"content": json.dumps({"fields": comparisons})}}).encode()
    return assistant


def comparison(**changes):
    return {"field_id": "p0.composition_pct.C", "status": "discrepancy", "raw_value": "13",
            "source_id": "t0r1c1", "header_id": "t0r0c1", **changes}


def detail(cert):
    return cert["products"][0]["observations"]["composition_pct"]["C"]


def test_backend_calculates_scale_preserves_values_and_overrules_model_match():
    cert = certificate()
    assistant = client([comparison(status="matches")])
    assert verify_fields(assistant, document(), cert)["status"] == "needs_review"
    result = detail(cert)["verification"]
    assert result["status"] == "discrepancy"
    assert result["normalized_value"] == .0013
    assert result["raw_value"] == "13" and result["header_text"] == "C 10^-4"
    assert result["page_number"] == 1 and result["bbox"]["x0"] == 10
    assert detail(cert)["normalized_value"] == .13
    assert cert["products"][0]["composition_pct"]["C"] == .13
    payload = json.loads(assistant.opener.open.call_args.args[0].data)
    assert payload["format"]["additionalProperties"] is False
    assert "normalized_value" in payload["messages"][1]["content"]


def test_match_is_backend_comparison_not_model_approval():
    cert = certificate(.0013)
    assert verify_fields(client([comparison()]), document(), cert)["status"] == "success"
    assert detail(cert)["verification"]["status"] == "matches"


def test_dimension_uses_backend_units_and_semantic_header():
    cert = {"products": [{"product_id": "A", "observations": {
        "width_mm": {"raw_value": "2", "normalized_value": 2}}}]}
    table = TableRegion(1, BoundingBox(0, 0, 300, 100), (("Coil", "Width in"), ("A", "2")))
    layout = DocumentLayout("test.pdf", "hash", (PageLayout(1, 600, 800, 0, PageSource.DIGITAL, tables=(table,)),))
    verify_fields(client([comparison(field_id="p0.width_mm", raw_value="2")]), layout, cert)
    proposed = cert["products"][0]["observations"]["width_mm"]["verification"]
    assert proposed["status"] == "discrepancy" and proposed["normalized_value"] == 50.8
    assert proposed["unit"] == "mm"


def test_zero_is_verified_and_missing_value_is_not_silently_zero():
    table = TableRegion(1, BoundingBox(0, 0, 300, 100), (("Coil", "C %"), ("A", "0")))
    layout = DocumentLayout("test.pdf", "hash", (PageLayout(1, 600, 800, 0, PageSource.DIGITAL, tables=(table,)),))
    cert = certificate(None)
    verify_fields(client([comparison(raw_value="0")]), layout, cert)
    assert detail(cert)["normalized_value"] is None
    assert detail(cert)["verification"]["normalized_value"] == 0
    assert detail(cert)["verification"]["status"] == "discrepancy"


def test_shared_heat_does_not_authorize_a_different_rolls_cell():
    table = TableRegion(1, BoundingBox(0, 0, 300, 100), (
        ("Coil", "C 10^-4", "Heat"), ("A", "13", "H1"), ("B", "20", "H1")))
    layout = DocumentLayout("test.pdf", "hash", (PageLayout(1, 600, 800, 0, PageSource.DIGITAL, tables=(table,)),))
    cert = certificate()
    verify_fields(client([comparison(raw_value="20", source_id="t0r2c1")]), layout, cert)
    assert detail(cert)["verification"]["status"] == "not_verifiable"


def test_known_adapter_also_runs_verification(monkeypatch):
    from backend.app.application.certificate_extraction import CertificateExtractionService
    import backend.app.application.certificate_extraction as module
    monkeypatch.setattr(module, "evaluate_format_profiles", lambda *args, **kwargs: ("known", 1, []))
    reader, registry, adapter = MagicMock(), MagicMock(), MagicMock()
    reader.read.return_value = document()
    registry.match_profile.return_value = adapter
    adapter.name = "known_adapter"
    adapter.extract.return_value = {"rows": [{"product_id": "A", "chemistry": {"C": "13"},
                                              "chemistry_scales": {"C": -2}}]}
    from backend.app.certificate_parser.mill_certificate import normalize_certificate
    normalized = normalize_certificate(adapter.extract.return_value)
    # Use one verified field so this test isolates the known-adapter routing.
    normalized["products"][0]["observations"] = {"composition_pct": {"C": detail(certificate())}}
    normalized["products"][0].update(form=None, coiled=None, rolling=None)
    monkeypatch.setattr(module, "normalize_certificate", lambda raw: normalized)
    assistant = client([comparison()])
    result = CertificateExtractionService(reader, registry, ollama_extractor=assistant).analyze_pdf("test.pdf")
    assert result["adapter"] == "known_adapter" and result["status"] == "needs_review"
    assert detail(normalized)["verification"]["status"] == "discrepancy"


@pytest.mark.parametrize("changes", [
    {"raw_value": "3"}, {"source_id": "missing"}, {"header_id": "t0r0c2"},
    {"source_id": "t0r2c1", "raw_value": "20"}, {"header_id": "t0r1c1"},
])
def test_invalid_literal_column_and_other_roll_are_not_verifiable(changes):
    cert = certificate()
    verify_fields(client([comparison(**changes)]), document(), cert)
    assert detail(cert)["verification"]["status"] == "not_verifiable"
    assert "normalized_value" not in detail(cert)["verification"]


@pytest.mark.parametrize("rows", [[], [comparison(), comparison()], [comparison(field_id="p9.unknown")]])
def test_missing_duplicate_and_unknown_fields_reject_section(rows):
    cert = certificate()
    assert verify_fields(client(rows), document(), cert)["status"] == "error"
    assert detail(cert)["normalized_value"] == .13


def test_no_evidence_does_not_become_match_or_zero():
    cert = certificate(None)
    verify_fields(client([comparison(status="not_verifiable", raw_value=None, source_id=None, header_id=None)]), document(), cert)
    assert detail(cert)["verification"]["status"] == "not_verifiable"
    assert detail(cert)["normalized_value"] is None


def test_timeout_size_limit_and_cancellation_preserve_original():
    assistant = client([comparison()])
    assistant.opener.open.side_effect = TimeoutError()
    cert = certificate()
    assert verify_fields(assistant, document(), cert)["status"] == "error"
    assert detail(cert)["verification"]["error_code"] == "TimeoutError"
    assistant.settings.ollama_max_page_chars = 1000
    large = certificate()
    large["products"][0]["product_id"] = "x" * 2000
    assistant.opener.reset_mock()
    assert verify_fields(assistant, document(), large)["status"] == "error"
    assistant.opener.open.assert_not_called()
    with pytest.raises(OcrCancellationRequested):
        verify_fields(assistant, document(), certificate(), lambda: True)


def test_acceptance_uses_saved_proposal_and_preserves_audit_and_citations():
    cert = certificate()
    verify_fields(client([comparison()]), document(), cert)
    previous = Observation(id=8, certificate_id=1, product_id=2, field_path="composition_pct.C",
        raw_value_json="13", normalized_value_json=.13, verification_json=detail(cert)["verification"],
        is_current=True)
    session = MagicMock()
    session.get.return_value = previous
    service = ReviewService(Settings(_env_file=None))
    service._sync_entity_field = MagicMock()
    replacement = service.correct_observation(session, observation_id=8, normalized_value=99,
        raw_value="invented", unit="wrong", person_name="Ana", reason="Revisé el encabezado",
        accept_verification=True)
    assert replacement.normalized_value_json == .0013 and replacement.raw_value_json == "13"
    assert replacement.unit == "%" and replacement.supersedes_id == 8
    assert replacement.page_number == 1 and "C 10^-4" in replacement.source_text
    assert previous.normalized_value_json == .13 and previous.is_current is False
    assert session.add.call_args_list[1].args[0].person_name == "Ana"


def test_unverifiable_or_superseded_proposal_cannot_be_accepted():
    session = MagicMock()
    previous = Observation(id=8, field_path="width_mm", is_current=True, verification_json={"status": "error"})
    session.get.return_value = previous
    with pytest.raises(ConflictError):
        ReviewService(Settings(_env_file=None)).correct_observation(session, observation_id=8,
            normalized_value=None, raw_value=None, unit=None, person_name="Ana", reason="Revisado",
            accept_verification=True)
    assert previous.is_current


def test_openapi_documents_verification_and_acceptance():
    from backend.app.api.app import create_app
    schema = create_app(Settings(_env_file=None)).openapi()
    assert "verification" in schema["components"]["schemas"]["CertificateObservationRead"]["properties"]
    assert "accept_verification" in schema["components"]["schemas"]["CorrectionRequest"]["properties"]


@pytest.mark.parametrize("vision,render_error,expected", [
    (True, False, "discrepancy"), (False, False, "not_verifiable"),
    (True, True, "not_verifiable"),
])
def test_visual_correction_requires_image_preserves_ocr_and_handles_render_failure(tmp_path, vision, render_error, expected):
    original = document()
    page = original.pages[0]
    layout = DocumentLayout("scan.pdf", "hash", (PageLayout(
        1, page.width, page.height, 0, PageSource.OCR, tables=page.tables),))
    pdf = tmp_path / "scan.pdf"
    pdf.write_bytes(b"placeholder: rendering is mocked")
    assistant = client([comparison(raw_value="33")])
    assistant.supports_vision = MagicMock(return_value=vision)
    assistant.page_image = MagicMock(return_value="original-image-base64",
                                    side_effect=ValueError("render failed") if render_error else None)
    cert = certificate()
    summary = verify_fields(assistant, layout, cert, pdf_path=pdf)
    assert detail(cert)["verification"]["status"] == expected
    assert detail(cert)["raw_value"] == "13" and detail(cert)["normalized_value"] == .13
    payload = json.loads(assistant.opener.open.call_args.args[0].data)
    if expected == "discrepancy":
        proposal = detail(cert)["verification"]
        assert proposal["normalized_value"] == .0033
        assert proposal["source"] == "ollama_visual"
        assert proposal["ocr_source_text"] == "13" and proposal["source_text"] == "33"
        assert payload["messages"][1]["images"] == ["original-image-base64"]
    else:
        assert "images" not in payload["messages"][1]
    if render_error:
        assert summary["visual_error"] == "ValueError"


def test_vision_does_not_allow_another_rolls_value(tmp_path):
    page = document().pages[0]
    layout = DocumentLayout("scan.pdf", "hash", (PageLayout(
        1, page.width, page.height, 0, PageSource.OCR, tables=page.tables),))
    pdf = tmp_path / "scan.pdf"
    pdf.touch()
    assistant = client([comparison(raw_value="33", source_id="t0r2c1")])
    assistant.supports_vision = MagicMock(return_value=True)
    assistant.page_image = MagicMock(return_value="image")
    cert = certificate()
    verify_fields(assistant, layout, cert, pdf_path=pdf)
    assert detail(cert)["verification"]["error_code"] == "invalid_evidence"
    assert detail(cert)["normalized_value"] == .13


def test_real_snapshot_section_excludes_adjacent_rolls():
    from backend.tests.unit.test_real_mill_ocr_layouts import read_snapshot
    from backend.app.certificate_parser.generic_extractor import GenericCertificateExtractor
    from backend.app.infrastructure.ollama_verification import _section_sources
    layout = read_snapshot(3)
    product = GenericCertificateExtractor().extract(layout).certificate["products"][2]
    observation = product["observations"]["composition_pct"]["C"]
    sources = _section_sources(layout.pages[0], {"p0.composition_pct.C": {
        "product_id": product["product_id"], "heat_no": product["heat_no"],
        "field_path": "composition_pct.C", "bbox": observation["bbox"],
    }})
    assert any(source["text"] == "14159491" for source in sources.values())
    assert not any(source["text"] in {"14159482", "14159492"} for source in sources.values())
    assert any(source["text"] == "C 10^-2" for source in sources.values())


@pytest.mark.parametrize("rotation,size,box", [
    (90, (10, 20), dict(x0=0, top=0, x1=10, bottom=10)),
    (180, (20, 10), dict(x0=0, top=0, x1=10, bottom=10)),
    (270, (10, 20), dict(x0=0, top=10, x1=10, bottom=20)),
])
def test_visual_crop_uses_the_same_orientation_as_ocr(monkeypatch, rotation, size, box):
    import base64
    from io import BytesIO
    from types import SimpleNamespace
    import pdfplumber
    from PIL import Image
    original = Image.new("RGB", (20, 10), "black")
    original.paste("red", (10, 0, 20, 10))
    page = SimpleNamespace(width=20, height=10, bbox=(0, 0, 20, 10),
                           to_image=lambda **kwargs: SimpleNamespace(original=original))
    pdf = MagicMock()
    pdf.__enter__.return_value.pages = [page]
    monkeypatch.setattr(pdfplumber, "open", lambda path: pdf)
    encoded = OllamaExtractor.page_image("fake.pdf", 1, box, rotation=rotation, expected_size=size)
    rendered = Image.open(BytesIO(base64.b64decode(encoded)))
    assert rendered.size == (10, 10)
    assert rendered.getpixel((5, 5)) == (255, 0, 0)
    with pytest.raises(ValueError, match="incompatibles"):
        OllamaExtractor.page_image("fake.pdf", 1, box, rotation=rotation, expected_size=(99, 99))


def test_missing_ocr_cell_can_receive_a_visual_proposal_without_filling_the_original(tmp_path):
    from backend.app.domain.document import TextBlock
    blocks = (TextBlock(1, "Width mm", BoundingBox(80, 20, 120, 30)),
              TextBlock(1, "A", BoundingBox(10, 100, 30, 110)))
    layout = DocumentLayout("scan.pdf", "hash", (PageLayout(1, 600, 800, 0, PageSource.OCR, blocks),))
    cert = {"products": [{"product_id": "A", "observations": {
        "width_mm": {"raw_value": None, "normalized_value": None}}}]}
    pdf = tmp_path / "scan.pdf"
    pdf.touch()
    assistant = client([comparison(field_id="p0.width_mm", raw_value="900",
                                   source_id="missing:p0.width_mm", header_id="b0")])
    assistant.supports_vision = MagicMock(return_value=True)
    assistant.page_image = MagicMock(return_value="image")
    verify_fields(assistant, layout, cert, pdf_path=pdf)
    original = cert["products"][0]["observations"]["width_mm"]
    assert original["raw_value"] is None and original["normalized_value"] is None
    assert original["verification"]["normalized_value"] == 900
    assert original["verification"]["bbox"]["top"] == 100
    payload = json.loads(assistant.opener.open.call_args.args[0].data)
    assert "missing:p0.width_mm" in payload["format"]["$defs"]["FieldComparison"]["properties"]["source_id"]["anyOf"][0]["enum"]
