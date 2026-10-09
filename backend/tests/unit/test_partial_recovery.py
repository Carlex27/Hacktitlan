from unittest.mock import MagicMock

import pytest

from backend.app.domain.document import BoundingBox, DocumentLayout, PageLayout, PageSource, TableRegion
from backend.app.infrastructure.partial_recovery import recover_missing_fields
from backend.app.infrastructure.ocr import OcrCancellationRequested


def layout():
    table = TableRegion(1, BoundingBox(0, 0, 300, 100), (
        ("Coil", "Heat", "Width mm", "C 10^-2"),
        ("A", "H1", "900", "33"), ("B", "H2", "1000", "44")))
    return DocumentLayout("new-supplier.pdf", "hash", (PageLayout(1, 600, 800, 0, PageSource.DIGITAL, tables=(table,)),))


def candidate():
    box = dict(x0=0, top=0, x1=300, bottom=100)
    return {"products": [{"product_id": "A", "heat_no": "H1", "observations": {
        "width_mm": {"raw_value": "900", "normalized_value": 900, "bbox": box},
        "composition_pct": {"C": {"raw_value": "33", "normalized_value": .33, "bbox": box}}},
        "evidence": [{"field_path": "width_mm", "source_id": "t0r1c2", "header_text": "Width mm"},
                     {"field_path": "composition_pct.C", "source_id": "t0r1c3", "header_text": "C 10^-2"}]}]}


def test_partial_recovery_proposes_missing_fields_without_changing_product():
    client = MagicMock()
    client.settings.ollama_model = "local-model"
    client.extract.return_value = candidate()
    original = {"product_id": "A", "heat_no": "H1", "width_mm": None, "thickness_mm": 1.8, "composition_pct": {}}
    result = recover_missing_fields(client, layout(), {"products": [original]})
    assert result["proposed_fields"] == 2
    assert original["width_mm"] is None and original["composition_pct"] == {}
    assert original["thickness_mm"] == 1.8
    assert original["observations"]["width_mm"]["normalized_value"] is None
    assert original["observations"]["width_mm"]["verification"]["normalized_value"] == 900
    assert original["observations"]["composition_pct"]["C"]["verification"]["normalized_value"] == .33
    assert client.extract.call_args.kwargs["product_ids"] == ["A"]


@pytest.mark.parametrize("mismatch", ["product", "heat", "row", "duplicate"])
def test_partial_recovery_rejects_unassociated_or_ambiguous_products(mismatch):
    proposal = candidate()
    product = proposal["products"][0]
    if mismatch == "product": product["product_id"] = "B"
    if mismatch == "heat": product["heat_no"] = "H2"
    if mismatch == "row":
        product["evidence"][0]["source_id"] = "t0r2c2"
        product["evidence"][1]["source_id"] = "t0r2c3"
    if mismatch == "duplicate": proposal["products"].append(product.copy())
    client = MagicMock()
    client.extract.return_value = proposal
    original = {"product_id": "A", "heat_no": "H1", "width_mm": None, "thickness_mm": 1.8, "composition_pct": {}}
    result = recover_missing_fields(client, layout(), {"products": [original]})
    assert result["proposed_fields"] == 0
    assert "observations" not in original


def test_partial_recovery_failure_and_cancellation_keep_original():
    client = MagicMock()
    client.extract.side_effect = TimeoutError()
    original = {"product_id": "A", "heat_no": "H1", "width_mm": None, "thickness_mm": 1.8, "composition_pct": {}}
    result = recover_missing_fields(client, layout(), {"products": [original]})
    assert result["errors"][0]["error_code"] == "TimeoutError"
    assert "observations" not in original
    with pytest.raises(OcrCancellationRequested):
        recover_missing_fields(client, layout(), {"products": [original]}, lambda: True)


def test_partial_recovery_keeps_existing_visual_proposal_and_zero_values():
    client = MagicMock()
    original = {"product_id": "A", "heat_no": "H1", "width_mm": None, "thickness_mm": 1.8,
                "composition_pct": {"C": 0}, "observations": {
                    "width_mm": {"raw_value": None, "normalized_value": None,
                                 "verification": {"status": "discrepancy", "normalized_value": 900}}}}
    result = recover_missing_fields(client, layout(), {"products": [original]})
    assert result["proposed_fields"] == 0
    client.extract.assert_not_called()
    assert original["composition_pct"]["C"] == 0
    assert original["observations"]["width_mm"]["verification"]["normalized_value"] == 900
