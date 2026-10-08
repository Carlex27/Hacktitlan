from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from backend.app.config import Settings
from backend.app.domain.document import DocumentLayout, PageLayout, PageSource
from backend.app.infrastructure.ocr.hardware import GpuDevice, HardwareProfile
from backend.app.infrastructure.ocr.reader import (
    OcrCancellationRequested,
    PaddleStructureReader,
)
from backend.app.infrastructure.ocr.runtime import (
    OcrRuntimeStatus,
    probe_ocr_runtime,
    run_smoke_check,
)


def hardware(*, with_gpu: bool = True) -> HardwareProfile:
    gpus = (
        (GpuDevice("NVIDIA", "Test GPU", 8192, "600.00", "12.0"),)
        if with_gpu
        else ()
    )
    return HardwareProfile(
        architecture="amd64",
        operating_system="Windows 11",
        total_memory_mb=16 * 1024,
        available_memory_mb=8 * 1024,
        gpus=gpus,
        compatibility="supported",
        reasons=("compatible",),
    )


def unreadable_layout() -> DocumentLayout:
    return DocumentLayout(
        "scan.pdf",
        "abc",
        (PageLayout(1, 612, 792, 0, PageSource.UNREADABLE),),
    )


class FakeDigitalReader:
    def read(self, _path):
        return unreadable_layout()


def runtime_status(*, healthy: bool, device: str | None) -> OcrRuntimeStatus:
    return OcrRuntimeStatus(
        enabled=True,
        installed=healthy,
        healthy=healthy,
        compatibility="supported",
        selected_device=device,
        paddle_version="3.3.0" if healthy else None,
        paddleocr_version="3.7.0" if healthy else None,
        hardware=hardware(),
        message="test",
    )


def test_missing_optional_runtime_uses_safe_needs_ocr_path():
    settings = Settings(ocr_enabled=True)
    reader = PaddleStructureReader(
        settings,
        digital_reader=FakeDigitalReader(),
        runtime_probe=lambda _settings: runtime_status(healthy=False, device=None),
    )

    result = reader.read("ignored.pdf")

    assert result.requires_ocr
    assert result.metadata["ocr"]["installed"] is False


def test_runtime_prefers_validated_nvidia_gpu():
    paddle = SimpleNamespace(
        __version__="3.3.0",
        device=SimpleNamespace(is_compiled_with_cuda=lambda: True),
    )
    paddleocr = SimpleNamespace(__version__="3.7.0")
    modules = {"paddle": paddle, "paddleocr": paddleocr}

    status = probe_ocr_runtime(
        Settings(ocr_enabled=True, ocr_device="auto"),
        hardware=hardware(),
        package_exists=lambda _name: True,
        importer=modules.__getitem__,
    )

    assert status.healthy
    assert status.selected_device == "gpu:0"


def test_runtime_falls_back_to_cpu_when_gpu_build_is_unavailable():
    paddle = SimpleNamespace(
        __version__="3.3.0",
        device=SimpleNamespace(is_compiled_with_cuda=lambda: False),
    )
    modules = {
        "paddle": paddle,
        "paddleocr": SimpleNamespace(__version__="3.7.0"),
    }

    status = probe_ocr_runtime(
        Settings(ocr_enabled=True, ocr_device="gpu:0"),
        hardware=hardware(),
        package_exists=lambda _name: True,
        importer=modules.__getitem__,
    )

    assert status.healthy
    assert status.selected_device == "cpu"
    assert "CPU" in status.message


def test_pp_structure_output_preserves_text_confidence_geometry_and_table():
    pipeline_arguments = {}

    class FakeResult:
        json = {
            "res": {
                "page_index": 0,
                "overall_ocr_res": {
                    "rec_texts": ["MILL TEST CERTIFICATE", "low confidence"],
                    "rec_scores": [0.98, 0.20],
                    "rec_polys": [
                        [[10, 20], [210, 20], [210, 40], [10, 40]],
                        [[10, 50], [100, 50], [100, 65], [10, 65]],
                    ],
                },
                "table_res_list": [
                    {
                        "pred_html": (
                            "<table><tr><th>COIL NO.</th><th>HEAT NO.</th></tr>"
                            "<tr><td>C1</td><td>H1</td></tr></table>"
                        ),
                        "cell_box_list": [
                            [[10, 100], [110, 100], [110, 120], [10, 120]],
                            [[110, 100], [210, 100], [210, 120], [110, 120]],
                        ],
                    }
                ],
            }
        }

    class FakePipeline:
        def predict(self, **kwargs):
            pipeline_arguments["predict"] = kwargs
            return [FakeResult()]

    def factory(**kwargs):
        pipeline_arguments["init"] = kwargs
        return FakePipeline()

    reader = PaddleStructureReader(
        Settings(ocr_enabled=True, ocr_min_confidence=0.5),
        digital_reader=FakeDigitalReader(),
        runtime_probe=lambda _settings: runtime_status(healthy=True, device="gpu:0"),
        pipeline_factory=factory,
    )

    result = reader.read(Path("ignored.pdf"))

    assert not result.requires_ocr
    assert result.pages[0].source == PageSource.OCR
    assert [block.text for block in result.pages[0].blocks] == ["MILL TEST CERTIFICATE"]
    assert result.pages[0].blocks[0].confidence == 0.98
    assert result.pages[0].tables[0].rows == (
        ("COIL NO.", "HEAT NO."),
        ("C1", "H1"),
    )
    assert pipeline_arguments["init"]["device"] == "gpu:0"
    assert pipeline_arguments["predict"]["use_doc_orientation_classify"] is True


def test_gpu_inference_failure_retries_once_on_cpu():
    devices: list[str] = []

    class FakeResult:
        json = {
            "res": {
                "page_index": 0,
                "overall_ocr_res": {
                    "rec_texts": ["HEAT NO H1"],
                    "rec_scores": [0.99],
                    "rec_polys": [[[0, 0], [100, 0], [100, 10], [0, 10]]],
                },
            }
        }

    class FakePipeline:
        def __init__(self, device: str) -> None:
            self.device = device

        def predict(self, **_kwargs):
            if self.device == "gpu:0":
                raise RuntimeError("simulated GPU allocation error")
            return [FakeResult()]

    def factory(**kwargs):
        devices.append(kwargs["device"])
        return FakePipeline(kwargs["device"])

    reader = PaddleStructureReader(
        Settings(ocr_enabled=True),
        digital_reader=FakeDigitalReader(),
        runtime_probe=lambda _settings: runtime_status(healthy=True, device="gpu:0"),
        pipeline_factory=factory,
    )

    result = reader.read("ignored.pdf")

    assert devices == ["gpu:0", "cpu"]
    assert result.pages[0].source == PageSource.OCR
    assert result.metadata["ocr"]["selected_device"] == "cpu"
    assert "GPU falló" in result.metadata["ocr"]["message"]


def test_smoke_check_success_and_timing():
    class FakePipeline:
        def predict(self):
            return []

    settings = Settings(ocr_enabled=True, ocr_device="cpu")
    result = run_smoke_check(
        settings,
        runtime_probe=lambda _s: runtime_status(healthy=True, device="cpu"),
        pipeline_factory=lambda **_kw: FakePipeline(),
    )

    assert result["success"] is True
    assert result["effective_device"] == "cpu"
    assert result["elapsed_ms"] >= 0.0
    assert "Verificación OCR completada" in result["message"]


def test_smoke_check_gpu_fallback_to_cpu():
    devices: list[str] = []

    class FakePipeline:
        def __init__(self, device: str):
            self.device = device

        def predict(self):
            if self.device == "gpu:0":
                raise RuntimeError("CUDA initialization failed")

    def factory(**kw):
        devices.append(kw["device"])
        return FakePipeline(kw["device"])

    settings = Settings(ocr_enabled=True, ocr_device="gpu:0")
    result = run_smoke_check(
        settings,
        runtime_probe=lambda _s: runtime_status(healthy=True, device="gpu:0"),
        pipeline_factory=factory,
    )

    assert result["success"] is True
    assert result["effective_device"] == "cpu"
    assert devices == ["gpu:0", "cpu"]
    assert "GPU falló" in result["message"]


def test_sequential_page_processing_and_progress_callback():
    pages_reported: list[tuple[int, int]] = []

    class MultiPageDigitalReader:
        def read(self, _path):
            return DocumentLayout(
                "multi.pdf",
                "abc",
                (
                    PageLayout(1, 612, 792, 0, PageSource.UNREADABLE),
                    PageLayout(2, 612, 792, 0, PageSource.UNREADABLE),
                ),
            )

    class FakeResult:
        def __init__(self, page_index: int):
            self.json = {
                "res": {
                    "page_index": page_index,
                    "overall_ocr_res": {
                        "rec_texts": [f"PAGE {page_index + 1}"],
                        "rec_scores": [0.95],
                        "rec_polys": [[[10, 10], [50, 10], [50, 20], [10, 20]]],
                    },
                }
            }

    class FakePipeline:
        def predict(self, **_kw):
            return [FakeResult(0), FakeResult(1)]

    reader = PaddleStructureReader(
        Settings(ocr_enabled=True),
        digital_reader=MultiPageDigitalReader(),
        runtime_probe=lambda _s: runtime_status(healthy=True, device="cpu"),
        pipeline_factory=lambda **_kw: FakePipeline(),
    )

    result = reader.read(
        "ignored.pdf",
        page_callback=lambda cur, tot: pages_reported.append((cur, tot)),
    )

    assert len(result.pages) == 2
    assert pages_reported == [(1, 2), (2, 2)]


def test_ocr_cancellation_between_pages():
    import pytest

    class FakeResult:
        json = {
            "res": {
                "page_index": 0,
                "overall_ocr_res": {
                    "rec_texts": ["PAGE 1"],
                    "rec_scores": [0.95],
                    "rec_polys": [[[0, 0], [10, 10]]],
                },
            }
        }

    class FakePipeline:
        def predict(self, **_kw):
            return [FakeResult()]

    reader = PaddleStructureReader(
        Settings(ocr_enabled=True),
        digital_reader=FakeDigitalReader(),
        runtime_probe=lambda _s: runtime_status(healthy=True, device="cpu"),
        pipeline_factory=lambda **_kw: FakePipeline(),
    )

    with pytest.raises(OcrCancellationRequested):
        reader.read("ignored.pdf", cancel_check=lambda: True)

