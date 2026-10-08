"""Select digital-only or optional local OCR ingestion."""

from backend.app.config import Settings
from backend.app.infrastructure.ocr.reader import PaddleStructureReader


def build_document_reader(settings: Settings) -> PaddleStructureReader:
    return PaddleStructureReader(settings)
