"""Optional PaddleOCR runtime discovery without importing it at application startup."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import importlib
import importlib.util
import time
from typing import Any, Callable

from backend.app.config import Settings
from backend.app.infrastructure.ocr.hardware import HardwareProfile, probe_hardware
from backend.app.infrastructure.ocr.models import OcrModelManager


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
    models: dict[str, Any] | None = None

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["hardware"] = self.hardware.as_dict()
        return data


def _package_exists(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def probe_ocr_runtime(
    settings: Settings,
    *,
    hardware: HardwareProfile | None = None,
    package_exists: Callable[[str], bool] = _package_exists,
    importer: Callable[[str], Any] = importlib.import_module,
    model_manager: OcrModelManager | None = None,
) -> OcrRuntimeStatus:
    hardware = hardware or probe_hardware()
    installed = package_exists("paddle") and package_exists("paddleocr")
    models = (model_manager or OcrModelManager(settings.model_root)).get_status().as_dict()

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
            models=models,
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
            models=models,
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
            models=models,
        )


def run_smoke_check(
    settings: Settings,
    *,
    runtime_probe: Callable[[Settings], OcrRuntimeStatus] = probe_ocr_runtime,
    pipeline_factory: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Execute a short verification check on the OCR runtime and record timing and device."""
    status = runtime_probe(settings)
    if not status.healthy or status.selected_device is None:
        return {
            "success": False,
            "requested_device": settings.ocr_device,
            "effective_device": None,
            "elapsed_ms": 0.0,
            "paddle_version": status.paddle_version,
            "paddleocr_version": status.paddleocr_version,
            "message": status.message,
        }

    start = time.perf_counter()
    effective_device = status.selected_device
    try:
        if pipeline_factory is not None:
            pipeline = pipeline_factory(device=effective_device)
            # Invoke predict if present
            if hasattr(pipeline, "predict"):
                pipeline.predict()
        else:
            from paddleocr import PPStructureV3

            _ = PPStructureV3(
                device=effective_device,
                lang=settings.ocr_language,
                cpu_threads=1,
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
                use_table_recognition=False,
                use_formula_recognition=False,
                use_chart_recognition=False,
            )
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        return {
            "success": True,
            "requested_device": settings.ocr_device,
            "effective_device": effective_device,
            "elapsed_ms": elapsed_ms,
            "paddle_version": status.paddle_version,
            "paddleocr_version": status.paddleocr_version,
            "message": f"Verificación OCR completada en {elapsed_ms} ms usando {effective_device}",
        }
    except Exception as exc:
        if effective_device != "cpu":
            # Retry once on CPU
            try:
                start_cpu = time.perf_counter()
                if pipeline_factory is not None:
                    pipeline = pipeline_factory(device="cpu")
                    if hasattr(pipeline, "predict"):
                        pipeline.predict()
                else:
                    from paddleocr import PPStructureV3

                    _ = PPStructureV3(
                        device="cpu",
                        lang=settings.ocr_language,
                        cpu_threads=1,
                        use_doc_orientation_classify=False,
                        use_doc_unwarping=False,
                        use_table_recognition=False,
                        use_formula_recognition=False,
                        use_chart_recognition=False,
                    )
                elapsed_ms = round((time.perf_counter() - start_cpu) * 1000, 2)
                return {
                    "success": True,
                    "requested_device": settings.ocr_device,
                    "effective_device": "cpu",
                    "elapsed_ms": elapsed_ms,
                    "paddle_version": status.paddle_version,
                    "paddleocr_version": status.paddleocr_version,
                    "message": f"GPU falló ({type(exc).__name__}); verificación exitosa en CPU ({elapsed_ms} ms)",
                }
            except Exception as cpu_exc:
                elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
                return {
                    "success": False,
                    "requested_device": settings.ocr_device,
                    "effective_device": "cpu",
                    "elapsed_ms": elapsed_ms,
                    "paddle_version": status.paddle_version,
                    "paddleocr_version": status.paddleocr_version,
                    "message": f"Fallo en CPU tras fallo en GPU: {type(cpu_exc).__name__}",
                }
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        return {
            "success": False,
            "requested_device": settings.ocr_device,
            "effective_device": effective_device,
            "elapsed_ms": elapsed_ms,
            "paddle_version": status.paddle_version,
            "paddleocr_version": status.paddleocr_version,
            "message": f"Fallo en verificación OCR: {type(exc).__name__}",
        }
