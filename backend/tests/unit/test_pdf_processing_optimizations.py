import json
from unittest.mock import patch

import pytest

from backend.app.certificate_parser.metadata import _label, extract_metadata
from backend.app.domain.document import BoundingBox, DocumentLayout, PageLayout, PageSource, TextBlock
from backend.app.infrastructure.ollama_verification import _section_sources, _sources, verify_fields
from backend.tests.unit.test_ollama_verification import certificate, client, comparison, document
from backend.tests.unit.test_real_mill_ocr_layouts import read_snapshot


def test_metadata_label_cache_is_local_and_preserves_all_evidence():
    blocks = tuple(TextBlock(1, text, BoundingBox(10, y, 200, y + 10))
                   for text, y in [("Customer", 10), ("Customer", 40), ("Example buyer", 70)])
    layout = DocumentLayout("test.pdf", "hash", (PageLayout(1, 600, 800, 0, PageSource.DIGITAL, blocks),))
    expected = extract_metadata(layout)
    with patch("backend.app.certificate_parser.metadata._label", wraps=_label) as label:
        assert extract_metadata(layout) == expected
        calls = [call.args[0] for call in label.call_args_list]
        assert len(calls) == len(set(calls))
        count = label.call_count
        assert extract_metadata(layout) == expected
        assert label.call_count == count * 2


@pytest.mark.parametrize("sample", [1, 2, 3, 4, "2-refined", "3-refined", "4-refined"])
def test_metadata_matches_uncached_extraction_on_real_ocr_snapshots(sample):
    layout = read_snapshot(sample)
    with patch("backend.app.certificate_parser.metadata.cache", side_effect=lambda function: function):
        expected = extract_metadata(layout)
    assert extract_metadata(layout) == expected


def test_verification_builds_sources_once_per_page_and_preserves_requests():
    layout = document()
    cert = certificate(.0013)
    second = certificate(.002)["products"][0]
    second["product_id"] = "B"
    second["observations"]["composition_pct"]["C"]["raw_value"] = "20"
    cert["products"].append(second)
    assistant = client([comparison()])
    response = assistant.opener.open.return_value.__enter__.return_value
    response.read.side_effect = [json.dumps({"done": True, "message": {"content": json.dumps({
        "fields": [comparison(field_id=f"p{index}.composition_pct.C", raw_value=raw,
                              source_id=f"t0r{index + 1}c1")]})}}).encode()
        for index, raw in enumerate(("13", "20"))]
    with patch("backend.app.infrastructure.ollama_verification._sources", wraps=_sources) as sources:
        assert verify_fields(assistant, layout, cert)["status"] == "success"
        sources.assert_called_once_with(layout.pages[0])
    requests = assistant.opener.open.call_args_list
    assert len(requests) == 2
    for index, request in enumerate(requests):
        payload = json.loads(request.args[0].data)
        content = json.loads(payload["messages"][1]["content"])
        section = {f"p{index}.composition_pct.C": {
            "product_id": cert["products"][index]["product_id"], "heat_no": "H1",
            "field_path": "composition_pct.C", "bbox": None}}
        assert content["sources"] == _section_sources(layout.pages[0], section)
