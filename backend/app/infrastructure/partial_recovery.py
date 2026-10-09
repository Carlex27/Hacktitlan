"""Recover missing measurements as cited proposals, never overwrite extraction."""
from __future__ import annotations

from backend.app.domain.document import DocumentLayout, PageLayout
from backend.app.certificate_parser.vocabulary import match_column_semantic, detect_scale_exponent
from backend.app.infrastructure.ocr import OcrCancellationRequested
from backend.app.infrastructure.ollama_verification import FieldComparison, _sources, _validate


def recover_missing_fields(client, document, certificate, cancel_check=None):
    recovered = set()
    errors = []
    page_sources = {p.page_number: _sources(p) for p in document.pages}
    for product in certificate.get("products", []):
        missing = {key for key in ("width_mm", "thickness_mm") if product.get(key) is None}
        for sources in page_sources.values():
            for source in sources.values():
                category, element, _ = match_column_semantic(source["text"])
                if category == "chemistry" and detect_scale_exponent(source["text"]) is not None and product.get("composition_pct", {}).get(element) is None:
                    missing.add(f"composition_pct.{element}")
        for key in tuple(missing):
            observations = product.get("observations", {})
            detail = (observations.get("composition_pct", {}).get(key.split(".")[1], {})
                      if key.startswith("composition_pct.") else observations.get(key, {}))
            if detail.get("verification", {}).get("status") == "discrepancy":
                missing.remove(key)
        if not missing:
            continue
        identity = product.get("product_id")
        if not identity:
            continue
        for page in document.pages:
            anchors = [b for b in page.blocks if b.text.strip() == identity]
            tables = tuple(t for t in page.tables if any(identity in row for row in t.rows))
            if len(anchors) != 1 and not tables:
                continue
            if cancel_check and cancel_check():
                raise OcrCancellationRequested("Recuperación cancelada")
            blocks = ()
            if len(anchors) == 1:
                box = anchors[0].bbox
                blocks = tuple(b for b in page.blocks if b.bbox.bottom < box.top or
                               box.top - 2 <= (b.bbox.top + b.bbox.bottom) / 2 <= box.bottom + 2)
            region = PageLayout(page.page_number, page.width, page.height, page.rotation, page.source, blocks, tables)
            section = DocumentLayout(document.file_name, document.sha256, (region,), document.metadata)
            try:
                candidate = client.extract(section, cancel_check=cancel_check, product_ids=[identity])
                matches = [p for p in candidate.get("products", []) if p.get("product_id") == identity
                           and (p.get("heat_no") is None or p.get("heat_no") == product.get("heat_no"))]
                if len(matches) != 1:
                    continue
                sources = _sources(region)
                for key in missing:
                    observations = matches[0].get("observations", {})
                    detail = (observations.get("composition_pct", {}).get(key.split(".")[1])
                              if key.startswith("composition_pct.") else observations.get(key))
                    evidence = next((e for e in matches[0].get("evidence", []) if e.get("field_path") == key), None)
                    if not detail or detail.get("normalized_value") is None or not evidence:
                        continue
                    source = sources.get(evidence.get("source_id"))
                    if not source:
                        continue
                    if "table" not in source:
                        if len(anchors) != 1:
                            continue
                        b = source["bbox"]
                        if not box.top - 2 <= (b["top"] + b["bottom"]) / 2 <= box.bottom + 2:
                            continue
                    headers = [header_id for header_id, h in sources.items() if h["text"] == evidence.get("header_text")]
                    if len(headers) != 1:
                        continue
                    comparison = FieldComparison(field_id=key, status="discrepancy", raw_value=str(detail["raw_value"]),
                                                 source_id=evidence["source_id"], header_id=headers[0])
                    context = {"field_path": key, "product_id": identity, "heat_no": product.get("heat_no"),
                               "bbox": detail.get("bbox"), "normalized_value": None}
                    try:
                        proposal = _validate(comparison, context, sources, region)
                    except (ValueError, ArithmeticError, KeyError, TypeError):
                        continue
                    proposal["model"] = client.settings.ollama_model
                    observations = product.setdefault("observations", {})
                    chemical = key.startswith("composition_pct.")
                    target = observations.setdefault("composition_pct", {}) if chemical else observations
                    name = key.split(".")[1] if chemical else key
                    original = target.setdefault(name, {
                        "raw_value": None, "normalized_value": None, "unit": "%" if chemical else "mm"})
                    previous = original.get("verification") or {}
                    if previous.get("error_code") == "ambiguous_page_readings":
                        previous["alternatives"].append(proposal)
                        continue
                    if previous.get("status") == "discrepancy" and previous.get("normalized_value") != proposal["normalized_value"]:
                        original["verification"] = {"status": "not_verifiable", "model": client.settings.ollama_model,
                            "error_code": "ambiguous_page_readings", "alternatives": [previous, proposal]}
                        recovered.discard((identity, key))
                        continue
                    original["verification"] = proposal
                    recovered.add((identity, key))
            except OcrCancellationRequested:
                raise
            except Exception as exc:
                errors.append({"product_id": identity, "page_number": page.page_number, "error_code": type(exc).__name__})
    return {"status": "needs_review" if recovered else "error" if errors else "not_verifiable",
            "proposed_fields": len(recovered), "errors": errors}
