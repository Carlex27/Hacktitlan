from backend.app.infrastructure.ocr.geometry import (
    clamp_bbox,
    fallback_full_page_bbox,
    normalize_points_to_bbox,
    transform_bbox_rotation,
)
from backend.app.infrastructure.ocr.hardware import HardwareProfile, probe_hardware
from backend.app.infrastructure.ocr.manifest import (
    ModelFile,
    ModelPackageManifest,
    get_manifest,
)
from backend.app.infrastructure.ocr.models import (
    ModelPackageStatus,
    OcrModelManager,
)
from backend.app.infrastructure.ocr.reader import (
    OcrCancellationRequested,
    PaddleStructureReader,
)
from backend.app.infrastructure.ocr.runtime import (
    OcrRuntimeStatus,
    probe_ocr_runtime,
    run_smoke_check,
)

__all__ = [
    "HardwareProfile",
    "ModelFile",
    "ModelPackageManifest",
    "ModelPackageStatus",
    "OcrCancellationRequested",
    "OcrModelManager",
    "OcrRuntimeStatus",
    "PaddleStructureReader",
    "clamp_bbox",
    "fallback_full_page_bbox",
    "get_manifest",
    "normalize_points_to_bbox",
    "probe_hardware",
    "probe_ocr_runtime",
    "run_smoke_check",
    "transform_bbox_rotation",
]
