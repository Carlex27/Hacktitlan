"""Document-wide metadata with explicit labels and retained source evidence."""
from __future__ import annotations

import re

from backend.app.certificate_parser.vocabulary import METADATA_LABELS, normalize_term
from backend.app.domain.document import DocumentLayout


def _label(text: str) -> tuple[str, str] | None:
    clean = normalize_term(text)
    if re.match(r"^(?:sub|grade|grand)\s+total\b", clean):
        return None
    if re.search(r'\bstandard\s+technique\b', clean):
        return None
    if re.search(r"\bcustomer\s+(?:no|number|id)\b", clean):
        return None
    matches = [(key, alias) for key, aliases in METADATA_LABELS.items() for alias in aliases
               if re.search(r"(?<!\w)" + re.escape(alias) + r"(?!\w)", clean)]
    if not matches:
        generic = re.match(r"^(date|fecha|日期)(?:\s|$)", clean)
        if generic:
            matches.append(("issue_date", generic[1]))
    return max(matches, key=lambda pair: len(pair[1])) if matches else None


def extract_metadata(document: DocumentLayout) -> dict:
    candidates: dict[str, list[dict]] = {key: [] for key in METADATA_LABELS}

    def add(key, value, page, bbox, source, label=None):
        value = value.strip().lstrip(":： ")
        if not value or _label(value) or normalize_term(value) in {"refer notes", "see notes", "ver notas", "检验", "inspection", "insp"}:
            return
        candidates[key].append({"value": value, "page_number": page,
                                "bbox": bbox, "source_text": source, "label": label})

    for page in document.pages:
        blocks = [block for block in page.blocks if block.text.strip()]
        for block in blocks:
            match = _label(block.text)
            if not match:
                continue
            key, alias = match
            parts = re.split(r"[:：]", block.text, maxsplit=1)
            if len(parts) == 2:
                add(key, parts[1], page.page_number, block.bbox.as_dict(), block.text, alias)
                continue
            inline = re.match(r"\s*" + r"\W+".join(re.escape(word) for word in alias.split())
                              + r"\b\s+(.+)$", block.text, re.I)
            if inline:
                add(key, inline[1], page.page_number, block.bbox.as_dict(), block.text, alias)
                continue
            nearby = [item for item in blocks if item is not block and not _label(item.text)
                      and block.bbox.x1 - 5 <= item.bbox.x0 <= block.bbox.x1 + page.width * .15
                      and abs((item.bbox.top + item.bbox.bottom - block.bbox.top - block.bbox.bottom) / 2)
                      < max(8, block.bbox.bottom - block.bbox.top)]
            if nearby:
                if key.endswith("date"):
                    nearby = [item for item in nearby if re.search(r"\d", item.text)]
                    if not nearby:
                        continue
                value = min(nearby, key=lambda item: abs(item.bbox.x0 - block.bbox.x1))
                qualifiers = [item for item in blocks if key.endswith("date")
                              and re.search(r"\b(?:about|approx|circa)\b", item.text, re.I)
                              and abs(item.bbox.x0 - value.bbox.x0) < 10
                              and -2 <= value.bbox.top - item.bbox.bottom < 10]
                raw = " ".join(item.text for item in [*qualifiers, value])
                boxes = [item.bbox for item in [*qualifiers, value]]
                bbox = {"x0": min(b.x0 for b in boxes), "x1": max(b.x1 for b in boxes),
                        "top": min(b.top for b in boxes), "bottom": max(b.bottom for b in boxes)}
                add(key, raw, page.page_number, bbox, raw, block.text)
            else:
                below = [item for item in blocks if item is not block and not _label(item.text)
                         and 0 <= item.bbox.top - block.bbox.bottom <= max(15, block.bbox.bottom - block.bbox.top)
                         and max(item.bbox.x0, block.bbox.x0) < min(item.bbox.x1, block.bbox.x1)]
                if key.endswith("date"):
                    below = [item for item in below if re.search(r"\d", item.text)]
                if below:
                    distance = min(item.bbox.top - block.bbox.bottom for item in below)
                    for value in below:
                        if value.bbox.top - block.bbox.bottom <= distance + 2:
                            add(key, value.text, page.page_number, value.bbox.as_dict(), value.text, block.text)
        for table in page.tables:
            for row in table.rows:
                for column, cell in enumerate(row[:-1]):
                    match = _label(cell or "")
                    if match and row[column + 1]:
                        add(match[0], str(row[column + 1]), page.page_number,
                            table.bbox.as_dict(), str(row[column + 1]), str(cell))

    # Explicit descriptions and company names can live in notes or the letterhead.
    customers = {item["value"] for item in candidates["customer"]}
    find_supplier = not candidates["supplier"]
    find_product = not candidates["product_name"]
    for page in document.pages:
        for block in page.blocks:
            text = block.text.strip()
            if find_supplier and text not in customers and not (text.endswith("公司") and len(text) < 4) and re.search(
                    r"\b(?:corporation|company|co\.?\s*,?\s*ltd\.?|s\.?a\.?)\s*$|公司$", text, re.I):
                add("supplier", text, page.page_number, block.bbox.as_dict(), text)
            if find_product and re.search(
                    r"\b(?:hot|cold)[ -]+rolled\b.*\b(?:coil|sheet|strip|plate)\b", text, re.I):
                add("product_name", text, page.page_number, block.bbox.as_dict(), text)

    result = {key: next(iter(values)) if len(values := {item["value"] for item in items}) == 1 else None
              for key, items in candidates.items()}
    result["field_evidence"] = {key: items for key, items in candidates.items() if items}
    return result
