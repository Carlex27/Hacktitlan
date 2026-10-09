"""PP-StructureV3 adapter that converts local OCR output into domain layouts."""

from __future__ import annotations

from dataclasses import replace
from contextlib import ExitStack
import gc
from html.parser import HTMLParser
import logging
from pathlib import Path
from typing import Any, Callable

from backend.app.config import Settings
from backend.app.document_ingestion.pdf_reader import PdfPlumberReader
from backend.app.domain.document import (
    BoundingBox,
    DocumentLayout,
    PageLayout,
    PageSource,
    TableRegion,
    TextBlock,
)
from backend.app.infrastructure.ocr.geometry import (
    clamp_bbox,
    fallback_full_page_bbox,
    normalize_points_to_bbox,
)
from backend.app.infrastructure.ocr.runtime import OcrRuntimeStatus, probe_ocr_runtime
from backend.app.infrastructure.ocr.table_refinement import refine_cells

logger = logging.getLogger(__name__)


class OcrCancellationRequested(Exception):
    """Raised when an ongoing OCR job is cancelled by the user between pages."""


class _TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.rows: list[tuple[str | None, ...]] = []
        self._row: list[str | None] | None = None
        self._cell: list[str] | None = None
        self._spans: dict[int, tuple[int, str | None]] = {}
        self._colspan = 1
        self._rowspan = 1

    def _fill_spans(self) -> None:
        while self._row is not None and len(self._row) in self._spans:
            column = len(self._row)
            remaining, value = self._spans[column]
            self._row.append(value)
            if remaining == 1:
                del self._spans[column]
            else:
                self._spans[column] = (remaining - 1, value)

    def handle_starttag(self, tag: str, _attrs) -> None:
        if tag == "tr":
            self._row = []
            self._fill_spans()
        elif tag in {"td", "th"} and self._row is not None:
            self._fill_spans()
            self._cell = []
            attrs = dict(_attrs)
            self._colspan = max(1, min(100, int(attrs.get("colspan", "1"))))
            self._rowspan = max(1, min(100, int(attrs.get("rowspan", "1"))))

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"} and self._row is not None and self._cell is not None:
            value = " ".join("".join(self._cell).split())
            for _ in range(self._colspan):
                column = len(self._row)
                self._row.append(value or None)
                if self._rowspan > 1:
                    self._spans[column] = (self._rowspan - 1, value or None)
            self._cell = None
        elif tag == "tr" and self._row is not None:
            self._fill_spans()
            self.rows.append(tuple(self._row))
            self._row = None


class PaddleStructureReader:
    def __init__(
        self,
        settings: Settings,
        *,
        digital_reader: PdfPlumberReader | None = None,
        runtime_probe: Callable[[Settings], OcrRuntimeStatus] = probe_ocr_runtime,
        pipeline_factory: Callable[..., Any] | None = None,
    ) -> None:
        self.settings = settings
        self.digital_reader = digital_reader or PdfPlumberReader()
        self.runtime_probe = runtime_probe
        self.pipeline_factory = pipeline_factory
        self._pipeline: Any | None = None
        self._pipeline_device: str | None = None

    def read(
        self,
        path: str | Path,
        *,
        page_callback: Callable[[int, int], None] | None = None,
        cancel_check: Callable[[], bool] | None = None,
    ) -> DocumentLayout:
        original = self.digital_reader.read(path)
        if not original.requires_ocr or not self.settings.ocr_enabled:
            return original
        runtime = self.runtime_probe(self.settings)
        if not runtime.healthy or runtime.selected_device is None:
            return DocumentLayout(
                original.file_name,
                original.sha256,
                original.pages,
                {**original.metadata, "ocr": runtime.as_dict()},
            )

        if cancel_check and cancel_check():
            raise OcrCancellationRequested("Procesamiento OCR cancelado antes de iniciar inferencia")

        try:
            results = self._predict(path, runtime.selected_device, cancel_check=cancel_check,
                                    page_callback=page_callback, total_pages=len(original.pages))
        except Exception as exc:
            if isinstance(exc, OcrCancellationRequested):
                raise
            if runtime.selected_device == "cpu":
                raise
            logger.warning("ocr_gpu_fallback", extra={"error_type": type(exc).__name__})
            self.release()
            runtime = replace(
                runtime,
                selected_device="cpu",
                message=f"GPU falló ({type(exc).__name__}); se utilizó CPU",
            )
            results = self._predict(path, "cpu", cancel_check=cancel_check,
                                    page_callback=page_callback, total_pages=len(original.pages))

        ocr_pages = self._convert_results(
            results,
            original.pages,
            cancel_check=cancel_check,
        )
        pages = tuple(
            ocr_pages.get(page.page_number, page)
            if page.source is PageSource.UNREADABLE
            else page
            for page in original.pages
        )
        return DocumentLayout(
            original.file_name,
            original.sha256,
            pages,
            {**original.metadata, "ocr": runtime.as_dict()},
        )

    def _get_pipeline(self, device: str):
        if self._pipeline is None or self._pipeline_device != device:
            factory = self.pipeline_factory
            if factory is None:
                from paddleocr import PPStructureV3

                factory = PPStructureV3
            self._pipeline = factory(
                device=device,
                lang=self.settings.ocr_language,
                cpu_threads=self.settings.ocr_cpu_threads,
                use_doc_orientation_classify=True,
                use_textline_orientation=False,
                use_doc_unwarping=False,
                use_table_recognition=True,
                use_formula_recognition=False,
                use_chart_recognition=False,
            )
            self._pipeline_device = device
        return self._pipeline

    def _predict(
        self,
        path: str | Path,
        device: str,
        cancel_check: Callable[[], bool] | None = None,
        page_callback: Callable[[int, int], None] | None = None,
        total_pages: int = 0,
    ) -> list[Any]:
        if cancel_check and cancel_check():
            raise OcrCancellationRequested("Procesamiento OCR cancelado por solicitud del usuario")
        pipeline = self._get_pipeline(device)
        input_path = Path(path)
        results = []
        with ExitStack() as stack:
            pdf = None
            if input_path.is_file() and input_path.suffix.lower() == ".pdf":
                import numpy as np
                import pdfplumber
                from paddlex.inference.pipelines.components import rotate_image

                pdf = stack.enter_context(pdfplumber.open(input_path))
            predictions = iter(pipeline.predict(
                input=str(input_path), use_doc_orientation_classify=True,
                use_textline_orientation=False, use_doc_unwarping=False,
                use_table_recognition=True,
            ))
            close = getattr(predictions, "close", None)
            if callable(close):
                stack.callback(close)
            while True:
                if cancel_check and cancel_check():
                    raise OcrCancellationRequested("Procesamiento OCR cancelado entre páginas")
                try:
                    result = next(predictions)
                except StopIteration:
                    break
                page_index = len(results)
                if pdf is not None:
                    page = pdf.pages[page_index]
                    resolution = min(300, self.settings.ocr_max_page_dimension * 72 / max(page.width, page.height))
                    cell_image = np.array(page.to_image(resolution=resolution).original.convert("RGB"))[:, :, ::-1]
                    result["page_index"] = page_index
                    angle = result["doc_preprocessor_res"].get("angle", 0)
                    result["cell_image"] = rotate_image(cell_image, angle if angle >= 0 else 0)
                results.append(result)
                if page_callback:
                    page_callback(page_index + 1, total_pages)
        return results

    def release(self) -> None:
        self._pipeline = None
        self._pipeline_device = None
        gc.collect()

    def _convert_results(
        self,
        results: list[Any],
        original_pages: tuple[PageLayout, ...],
        page_callback: Callable[[int, int], None] | None = None,
        cancel_check: Callable[[], bool] | None = None,
    ) -> dict[int, PageLayout]:
        converted: dict[int, PageLayout] = {}
        total_pages = len(original_pages)

        for fallback_index, result in enumerate(results):
            if cancel_check and cancel_check():
                raise OcrCancellationRequested("Procesamiento OCR cancelado durante la conversión de páginas")

            payload = result.json if hasattr(result, "json") else result
            core = payload.get("res", payload)
            raw_page_index = core.get("page_index")
            page_index = fallback_index if raw_page_index is None else int(raw_page_index)
            page_number = page_index + 1
            if page_number > total_pages:
                continue

            original = original_pages[page_number - 1]
            page_w = original.width
            page_h = original.height
            page_rot = original.rotation

            img_w = core.get("img_w") or core.get("width")
            img_h = core.get("img_h") or core.get("height")
            image = None
            # JSON omits raster dimensions; use the oriented image held by Paddle's result.
            if hasattr(result, "get"):
                image = (result.get("doc_preprocessor_res") or {}).get("output_img")
                if image is not None and hasattr(image, "shape"):
                    img_h, img_w = image.shape[:2]
                    if (img_w > img_h) != (page_w > page_h):
                        page_w, page_h = page_h, page_w
                    page_rot = 0
            if img_w is not None:
                img_w = float(img_w)
            if img_h is not None:
                img_h = float(img_h)

            ocr = core.get("overall_ocr_res") or core
            texts = list(ocr.get("rec_texts") or [])
            scores = list(ocr.get("rec_scores") or [])
            polygons = list(ocr.get("rec_polys") or ocr.get("rec_boxes") or [])
            blocks: list[TextBlock] = []

            for index, text in enumerate(texts):
                confidence = float(scores[index]) if index < len(scores) else 0.0
                if not str(text).strip() or confidence < self.settings.ocr_min_confidence:
                    continue
                points = polygons[index] if index < len(polygons) else None
                if points:
                    box = normalize_points_to_bbox(
                        points,
                        page_width=page_w,
                        page_height=page_h,
                        image_width=img_w,
                        image_height=img_h,
                        rotation=page_rot,
                    )
                else:
                    box = fallback_full_page_bbox(page_w, page_h)

                blocks.append(
                    TextBlock(page_number, str(text), box, confidence, PageSource.OCR)
                )

            tables: list[TableRegion] = []
            for table in core.get("table_res_list") or []:
                parser = _TableParser()
                parser.feed(str(table.get("pred_html") or ""))
                cell_boxes = table.get("cell_box_list") or []
                if not parser.rows:
                    continue

                if cell_boxes:
                    boxes = [
                        normalize_points_to_bbox(
                            cb,
                            page_width=page_w,
                            page_height=page_h,
                            image_width=img_w,
                            image_height=img_h,
                            rotation=page_rot,
                        )
                        for cb in cell_boxes
                    ]
                    table_box = clamp_bbox(
                        BoundingBox(
                            min(b.x0 for b in boxes),
                            min(b.top for b in boxes),
                            max(b.x1 for b in boxes),
                            max(b.bottom for b in boxes),
                        ),
                        page_w,
                        page_h,
                    )
                else:
                    table_box = fallback_full_page_bbox(page_w, page_h)

                tables.append(TableRegion(page_number, table_box, tuple(parser.rows)))

            converted[page_number] = PageLayout(
                page_number=page_number,
                width=page_w,
                height=page_h,
                rotation=page_rot,
                source=PageSource.OCR if blocks else PageSource.UNREADABLE,
                blocks=tuple(blocks),
                tables=tuple(tables),
            )
            if image is not None and self._pipeline is not None:
                # shortcut: pinned PaddleX exposes the shared recognizer; revisit on OCR runtime upgrades.
                pipeline = getattr(self._pipeline, "paddlex_pipeline", None)
                ocr_pipeline = getattr(pipeline, "general_ocr_pipeline", None)
                recognizer = getattr(ocr_pipeline, "text_rec_model", None)
                if recognizer is not None:
                    cell_image = result.get("cell_image") if hasattr(result, "get") else None
                    converted[page_number] = refine_cells(converted[page_number], cell_image if cell_image is not None else image, recognizer, self.settings.ocr_min_confidence)

            if page_callback:
                page_callback(page_number, total_pages)

        return converted
