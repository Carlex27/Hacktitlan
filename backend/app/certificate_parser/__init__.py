from .mill_certificate import CertificateParseError, normalize_certificate

__all__ = ["CertificateParseError", "normalize_certificate"]
from backend.app.certificate_parser.detection import DocumentKind, detect_document_kind
from backend.app.certificate_parser.mill_certificate import (
    CertificateParseError,
    normalize_certificate,
)

__all__ = [
    "CertificateParseError",
    "DocumentKind",
    "detect_document_kind",
    "normalize_certificate",
]
