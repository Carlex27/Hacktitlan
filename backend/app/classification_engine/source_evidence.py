"""Managed, versioned navigation to the supplied legal source."""

from hashlib import sha256
import json
from pathlib import Path

from .catalog import DEFAULT_CATALOG_PATH, SourceProvidedCatalog

SOURCE_SHA256 = "756ed9e9d43676fe973e03948f3b299d3eaac998a3d13fdea7ba109e33786155"
SOURCE_PDF = DEFAULT_CATALOG_PATH.with_name("LIGIE-UNIFICADA-ACERO.pdf")
SOURCE_FILE_URL = f"/api/v1/rule-sources/{SOURCE_SHA256}/file"


def verified_source_pdf(source_hash: str) -> Path:
    if source_hash != SOURCE_SHA256 or not SOURCE_PDF.is_file():
        raise FileNotFoundError("La fuente normativa solicitada no está disponible")
    if sha256(SOURCE_PDF.read_bytes()).hexdigest() != SOURCE_SHA256:
        raise ValueError("El PDF normativo no coincide con su versión registrada")
    return SOURCE_PDF


def source_reference(
    catalog: SourceProvidedCatalog,
    rule_code: str,
    fraction: str | None = None,
    nico: str | None = None,
    evidence_fields: tuple[str, ...] = (),
    source_hash: str = SOURCE_SHA256,
) -> dict[str, object]:
    if source_hash != SOURCE_SHA256:
        return {}
    page: int | None = None
    bbox = None
    text = None
    if rule_code in {"chapter72.definition.other_alloy", "chapter72.definition.non_alloy"}:
        page = 7
        index = json.loads(DEFAULT_CATALOG_PATH.with_name("alloy-evidence.json").read_text(encoding="utf-8"))
        regions = [index[field.split(".", 1)[1].replace("Al_soluble", "Al_total")]
                   for field in evidence_fields if field.startswith("composition_pct.")
                   and field.split(".", 1)[1].replace("Al_soluble", "Al_total") in index]
        if regions:
            bbox = {**regions[0]["bbox"],
                    "x0": min(item["bbox"]["x0"] for item in regions),
                    "y0": min(item["bbox"]["y0"] for item in regions),
                    "x1": max(item["bbox"]["x1"] for item in regions),
                    "y1": max(item["bbox"]["y1"] for item in regions)}
            text = "\n".join(dict.fromkeys(item["source_text"] for item in regions))
    elif rule_code.startswith("chapter72.definition.stainless") or rule_code == "chapter72.definition.steel":
        page = 6
    elif rule_code == "chapter72.flat_rolled.definition":
        page = 8
    elif fraction:
        code = f"{fraction}{nico}" if rule_code.startswith("chapter72.nico.") and nico else fraction
        entry = catalog.get(code)
        if entry is not None:
            page, text = entry.page, entry.description
    return {
        "source_hash": SOURCE_SHA256,
        "legal_status": "SIN VIGENCIA — NO VERIFICADO",
        "file_url": SOURCE_FILE_URL,
        "page_number": page,
        "bbox": bbox,
        "source_text": text,
        "can_focus_region": bbox is not None,
        "fallback": None if bbox is not None else "full_page",
    }
