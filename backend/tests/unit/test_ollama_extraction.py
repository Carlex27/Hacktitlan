import json
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from backend.app.application.certificate_extraction import CertificateExtractionService
from backend.app.application.worker import Worker
from backend.app.certificate_parser.adapters import AdapterRegistry
from backend.app.certificate_parser.generic_extractor import GenericExtractionResult
from backend.app.config import Settings
from backend.app.domain.document import BoundingBox, DocumentLayout, PageLayout, PageSource, TextBlock
from backend.app.infrastructure.ocr import OcrCancellationRequested
from backend.app.infrastructure.ollama import OllamaExtractor


def layout(*texts):
    blocks = tuple(TextBlock(1, value, BoundingBox(0, i * 10, 100, i * 10 + 8))
                   for i, value in enumerate(texts))
    return DocumentLayout("sample.pdf", "hash", (PageLayout(1, 600, 800, 0, PageSource.DIGITAL, blocks),))


def field(name, value, source_id, header_id=None):
    return dict(field=name, value=value, source_id=source_id, header_id=header_id)


def extractor(fields, **settings):
    client = OllamaExtractor(Settings(_env_file=None, **settings))
    client.opener = MagicMock()
    content = json.dumps({"products": [{"fields": fields}]})
    client.opener.open.return_value.__enter__.return_value.read.return_value = json.dumps({
        "done": True, "message": {"content": content},
    }).encode()
    return client


def test_local_request_uses_configured_model_and_preserves_evidence_and_unknowns():
    client = extractor([
        field("product_id", "COIL-1", "b0"),
        field("thickness_mm", "0.1", "b2", "b1"),
        field("chemistry", "13", "b4", "b3"),
    ], ollama_model="qwen3.5:9b", ollama_timeout_seconds=12)
    result = client.extract(layout("COIL-1", "Thickness in", "0.1", "C 10^-4", "13"))
    product = result["products"][0]
    assert product["thickness_mm"] == 2.54
    assert product["composition_pct"]["C"] == .0013
    assert product["width_mm"] is None and product["coiled"] is None
    assert product["quantity"] is None and product["heat_no"] is None
    assert product["observations"]["thickness_mm"]["raw_value"] == "0.1"
    assert product["observations"]["thickness_mm"]["confidence"] is None
    assert product["evidence"][0]["bbox"] == dict(x0=0, top=0, x1=100, bottom=8)
    request = client.opener.open.call_args.args[0]
    body = json.loads(request.data)
    assert request.full_url == "http://127.0.0.1:11434/api/chat"
    assert body["model"] == "qwen3.5:9b" and body["stream"] is False
    assert body["format"]["additionalProperties"] is False
    assert client.opener.open.call_args.kwargs["timeout"] == 12


@pytest.mark.parametrize("fields,texts", [
    ([field("product_id", "INVENTED", "b0")], ["COIL-1"]),
    ([field("product_id", "COIL-1", "missing")], ["COIL-1"]),
    ([field("product_id", "1", "b0")], ["100"]),
    ([field("product_id", "COIL-1", "b0"), field("width_mm", "100", "b1")], ["COIL-1", "100"]),
    ([field("product_id", "COIL-1", "b0"), field("chemistry", "13", "b2", "b1")], ["COIL-1", "C", "13"]),
    ([field("product_id", "COIL-1", "b0"), field("product_id", "COIL-1", "b0")], ["COIL-1"]),
    ([field("product_id", "X" * 301, "b0")], ["X" * 301]),
])
def test_unverifiable_values_are_rejected(fields, texts):
    with pytest.raises(ValueError):
        extractor(fields).extract(layout(*texts))


def test_invalid_response_and_oversized_page_are_rejected():
    client = extractor([])
    client.opener.open.return_value.__enter__.return_value.read.return_value = b'{"done":false}'
    with pytest.raises(ValidationError):
        client.extract(layout("COIL-1"))
    client.opener.reset_mock()
    with pytest.raises(ValueError, match="no se truncó"):
        client.extract(layout("x" * 25000))
    client.opener.open.assert_not_called()


def service(client, certificate=None):
    reader = MagicMock()
    reader.read.return_value = layout("MILL TEST CERTIFICATE", "COIL-1")
    generic = MagicMock()
    generic.extract.return_value = GenericExtractionResult(
        certificate is not None, certificate, [], [], ["original reason"])
    return CertificateExtractionService(reader, AdapterRegistry(), generic, client)


def test_fallback_recovers_products_and_requires_review():
    result = service(extractor([field("product_id", "COIL-1", "b1")])).analyze_pdf("sample.pdf")
    assert result["status"] == "needs_review" and result["adapter"] == "ollama_local"
    assert result["certificate"]["products"][0]["product_id"] == "COIL-1"
    assert result["llm_assistance"]["status"] == "needs_review"


def test_existing_certificate_is_not_overwritten_by_proposal():
    original = {"products": [{"product_id": "ORIGINAL"}]}
    result = service(extractor([field("product_id", "COIL-1", "b1")]), original).analyze_pdf("sample.pdf")
    assert result["certificate"] is original
    assert result["llm_assistance"]["mode"] == "field_verification"
    assert result["llm_assistance"]["status"] == "needs_review"
    assert "candidate" not in result["llm_assistance"]
    client = extractor([])
    service(client, original).analyze_pdf("sample.pdf")
    client.opener.open.assert_not_called()


@pytest.mark.parametrize("failure", [TimeoutError(), ConnectionRefusedError(), ValueError("invalid JSON")])
def test_inference_failure_keeps_original_extraction_and_records_warning(failure):
    client = extractor([])
    client.opener.open.side_effect = failure
    original = {"products": [{"product_id": "ORIGINAL", "observations": {
        "width_mm": {"raw_value": "100", "normalized_value": 100}}}]}
    result = service(client, original).analyze_pdf("sample.pdf")
    assert result["certificate"] is original
    assert result["llm_assistance"]["status"] == "error"
    assert original["products"][0]["observations"]["width_mm"]["verification"]["error_code"] == type(failure).__name__
    assert "se conserva" in result["reasons"][-1]


def test_cancellation_propagates_without_inference():
    client = extractor([])
    with pytest.raises(OcrCancellationRequested):
        service(client).analyze_pdf("sample.pdf", cancel_check=lambda: True)
    client.opener.open.assert_not_called()


def test_worker_enable_switch_and_disabled_service_do_not_call_ollama():
    disabled = Worker(Settings(_env_file=None), MagicMock(), MagicMock())
    assert disabled.extractor.ollama_extractor is None
    enabled = Worker(Settings(_env_file=None, ollama_enabled=True), MagicMock(), MagicMock())
    assert isinstance(enabled.extractor.ollama_extractor, OllamaExtractor)
    assert "llm_assistance" not in service(None).analyze_pdf("sample.pdf")


@pytest.mark.parametrize("url", ["https://example.com", "http://10.0.0.1:11434",
                                "http://127.0.0.1/api", "http://user@localhost", "http://localhost:bad"])
def test_remote_or_malformed_servers_are_rejected(url):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, ollama_base_url=url)


def test_settings_read_environment(monkeypatch):
    monkeypatch.setenv("HACKTITLAN_OLLAMA_ENABLED", "true")
    monkeypatch.setenv("HACKTITLAN_OLLAMA_MODEL", "qwen3.5:9b")
    assert Settings(_env_file=None).ollama_enabled
    assert Settings(_env_file=None).ollama_model == "qwen3.5:9b"
    with pytest.raises(ValidationError):
        Settings(_env_file=None, ollama_model="qwen3.5:cloud")
