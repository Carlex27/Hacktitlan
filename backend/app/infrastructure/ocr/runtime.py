"""Optional PaddleOCR runtime discovery without importing it at application startup."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import importlib
import importlib.util
from typing import Any, Callable

from backend.app.config import Settings
from backend.app.infrastructure.ocr.hardware import HardwareProfile, probe_hardware


@dataclass(frozen=True)
class OcrRuntimeStatus:
    enabled: bool
    installed: bool
    healthy: bool
    compatibility: str
    selected_device: str | None
    paddle_version: str | None
    paddleocr_version: str | None
    hardware: HardwareProfile
    message: str

    def as_dict(self) -> dict[str, Any]:
        return {**asdict(self), "hardware": self.hardware.as_dict()}


def _package_exists(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def probe_ocr_runtime(
    settings: Settings,
    *,
    hardware: HardwareProfile | None = None,
    package_exists: Callable[[str], bool] = _package_exists,
    importer: Callable[[str], Any] = importlib.import_module,
) -> OcrRuntimeStatus:
    hardware = hardware or probe_hardware()
    installed = package_exists("paddle") and package_exists("paddleocr")
    if not installed:
        return OcrRuntimeStatus(
            enabled=settings.ocr_enabled,
            installed=False,
            healthy=False,
            compatibility=hardware.compatibility,
            selected_device=None,
            paddle_version=None,
            paddleocr_version=None,
            hardware=hardware,
            message="Paquete OCR no instalado",
        )

    try:
        paddle = importer("paddle")
        paddleocr = importer("paddleocr")
        cuda_ready = bool(paddle.device.is_compiled_with_cuda()) and bool(hardware.gpus)
        requested = settings.ocr_device
        selected_device = "gpu:0" if requested in {"auto", "gpu:0"} and cuda_ready else "cpu"
        message = "Runtime OCR disponible"
        if requested == "gpu:0" and not cuda_ready:
            message = "GPU solicitada no disponible; se utilizará CPU"
        return OcrRuntimeStatus(
            enabled=settings.ocr_enabled,
            installed=True,
            healthy=True,
            compatibility=hardware.compatibility,
            selected_device=selected_device,
            paddle_version=getattr(paddle, "__version__", None),
            paddleocr_version=getattr(paddleocr, "__version__", None),
            hardware=hardware,
            message=message,
        )
    except Exception as exc:
        return OcrRuntimeStatus(
            enabled=settings.ocr_enabled,
            installed=True,
            healthy=False,
            compatibility=hardware.compatibility,
            selected_device=None,
            paddle_version=None,
            paddleocr_version=None,
            hardware=hardware,
            message=f"Runtime OCR inválido: {type(exc).__name__}",
        )
