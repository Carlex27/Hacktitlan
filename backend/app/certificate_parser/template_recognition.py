"""Conservative recognition against immutable job snapshots."""
from pydantic import BaseModel

from backend.app.certificate_parser.templates import TemplateConfiguration, extractor_hash, preview_template
from backend.app.certificate_parser.regions import select_region
from backend.app.domain.document import DocumentLayout


class TemplateSnapshot(BaseModel):
    version_id: int
    format_id: int
    version_number: int
    configuration_sha256: str
    extractor_sha256: str
    configuration: TemplateConfiguration


def matches_template(document: DocumentLayout, configuration: TemplateConfiguration) -> bool:
    if len(configuration.recognition) < 2:
        return False
    pages = {page.page_number: page for page in document.pages}
    for anchor in configuration.recognition:
        page = pages.get(anchor.page_number)
        if page is None:
            return False
        evidence = select_region(page, anchor.region)
        if evidence.status != "success" or anchor.text.casefold() not in " ".join(evidence.text.split()).casefold():
            return False
    return True


def validate_snapshot(snapshot: TemplateSnapshot) -> None:
    if snapshot.configuration.sha256 != snapshot.configuration_sha256 or snapshot.extractor_sha256 != extractor_hash():
        raise ValueError("La versión del extractor o configuración cambió; vuelve a encolar el trabajo")


def extract_template(document: DocumentLayout, snapshot: TemplateSnapshot) -> dict:
    validate_snapshot(snapshot)
    preview = preview_template(document, snapshot.configuration)
    return {
        "status": "needs_ocr" if preview.status == "needs_ocr" else "needs_review",
        "adapter": "user_template",
        "certificate": preview.certificate,
        "template": snapshot.model_dump(mode="json", exclude={"configuration"}),
        "template_evidence": preview.evidence,
        "reasons": ["Plantilla de usuario: verificar la extracción antes de aprobar"] + [d.message for d in preview.diagnostics],
    }
