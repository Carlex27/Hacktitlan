"""PP-StructureV3 adapter that converts local OCR output into domain layouts."""

from __future__ import annotations

from dataclasses import replace
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
from backend.app.infrastructure.ocr.runtime import OcrRuntimeStatus, probe_ocr_runtime


logger = logging.getLogger(__name__)


class _TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.rows: list[tuple[str | None, ...]] = []
        self._row: list[str | None] | None = None
        self._cell: list[str] | None = None

    def handle_starttag(self, tag: str, _attrs) -> None:
        if tag == "tr":
            self._row = []
        elif tag in {"td", "th"} and self._row is not None:
            self._cell = []

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"} and self._row is not None and self._cell is not None:
            value = " ".join("".join(self._cell).split())
            self._row.append(value or None)
            self._cell = None
        elif tag == "tr" and self._row is not None:
            self.rows.append(tuple(self._row))
            self._row = None


def _bbox(points: Any) -> BoundingBox:
    coordinates = [(float(point[0]), float(point[1])) for point in points]
    return BoundingBox(
        min(point[0] for point in coordinates),
        min(point[1] for point in coordinates),
        max(point[0] for point in coordinates),
        max(point[1] for point in coordinates),
    )


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

    def read(self, path: str | Path) -> DocumentLayout:
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

        try:
            results = self._predict(path, runtime.selected_device)
        except Exception as exc:
            if runtime.selected_device == "cpu":
                raise
            logger.warning("ocr_gpu_fallback", extra={"error_type": type(exc).__name__})
            self.release()
            runtime = replace(
                runtime,
                selected_device="cpu",
                message=f"GPU falló ({type(exc).__name__}); se utilizó CPU",
            )
            results = self._predict(path, "cpu")
        ocr_pages = self._convert_results(results, original.pages)
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
                use_doc_unwarping=False,
                use_table_recognition=True,
                use_formula_recognition=False,
                use_chart_recognition=False,
            )
            self._pipeline_device = device
        return self._pipeline

    def _predict(self, path: str | Path, device: str) -> list[Any]:
        pipeline = self._get_pipeline(device)
        return list(
            pipeline.predict(
                input=str(Path(path)),
                use_doc_orientation_classify=True,
                use_doc_unwarping=False,
                use_table_recognition=True,
            )
        )

    def release(self) -> None:
        self._pipeline = None
        self._pipeline_device = None
        gc.collect()

    def _convert_results(
        self, results: list[Any], original_pages: tuple[PageLayout, ...]
    ) -> dict[int, PageLayout]:
        converted: dict[int, PageLayout] = {}
        for fallback_index, result in enumerate(results):
            payload = result.json if hasattr(result, "json") else result
            core = payload.get("res", payload)
            raw_page_index = core.get("page_index")
            page_index = fallback_index if raw_page_index is None else int(raw_page_index)
            page_number = page_index + 1
            if page_number > len(original_pages):
                continue
            ocr = core.get("overall_ocr_res") or core
            texts = list(ocr.get("rec_texts") or [])
            scores = list(ocr.get("rec_scores") or [])
            polygons = list(ocr.get("rec_polys") or ocr.get("rec_boxes") or [])
            blocks: list[TextBlock] = []
            for index, text in enumerate(texts):
                confidence = float(scores[index]) if index < len(scores) else 0.0
                if not str(text).strip() or confidence < self.settings.ocr_min_confidence:
                    continue
                points = polygons[index] if index < len(polygons) else [[0, index], [1, index + 1]]
                if len(points) == 4 and not isinstance(points[0], (list, tuple)):
                    x0, top, x1, bottom = map(float, points)
                    points = [[x0, top], [x1, bottom]]
                blocks.append(
                    TextBlock(page_number, str(text), _bbox(points), confidence, PageSource.OCR)
                )

            tables: list[TableRegion] = []
            for table in core.get("table_res_list") or []:
                parser = _TableParser()
                parser.feed(str(table.get("pred_html") or ""))
                cell_boxes = table.get("cell_box_list") or []
                if not parser.rows or not cell_boxes:
                    continue
                boxes = [_bbox(box) for box in cell_boxes]
                table_box = BoundingBox(
                    min(box.x0 for box in boxes),
                    min(box.top for box in boxes),
                    max(box.x1 for box in boxes),
                    max(box.bottom for box in boxes),
                )
                tables.append(TableRegion(page_number, table_box, tuple(parser.rows)))

            original = original_pages[page_number - 1]
            converted[page_number] = PageLayout(
                page_number=page_number,
                width=original.width,
                height=original.height,
                rotation=original.rotation,
                source=PageSource.OCR if blocks else PageSource.UNREADABLE,
                blocks=tuple(blocks),
                tables=tuple(tables),
            )
        return converted
