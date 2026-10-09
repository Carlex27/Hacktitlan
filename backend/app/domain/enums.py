"""Stable persisted states shared by the API and database."""

from enum import StrEnum


class FileStatus(StrEnum):
    READY = "ready"
    QUARANTINED = "quarantined"
    MISSING = "missing"


class ProcessingStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    NEEDS_REVIEW = "needs_review"
    NEEDS_OCR = "needs_ocr"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ApprovalStatus(StrEnum):
    DRAFT = "draft"
    NEEDS_REVIEW = "needs_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class JobKind(StrEnum):
    PREPARE_LAYOUT = "prepare_layout"
    TEST_CERTIFICATE_FORMAT = "test_certificate_format"
    EXTRACT_DOCUMENT = "extract_document"
    NORMALIZE_DOCUMENT = "normalize_document"
    RECLASSIFY = "reclassify"
    EXPORT_XLSX = "export_xlsx"
    BACKUP = "backup"


class RuleSetStatus(StrEnum):
    DRAFT = "draft"
    APPROVED = "approved"
    RETIRED = "retired"


class ExportStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class BackupStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    VERIFIED = "verified"
