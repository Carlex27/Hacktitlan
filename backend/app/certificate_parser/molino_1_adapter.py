"""Deterministic adapter for the BX Steel Posco Molino 1 certificate."""

from __future__ import annotations

import re
from dataclasses import replace

from backend.app.certificate_parser.adapters import AdapterMatch
from backend.app.certificate_parser.format_profiles import evaluate_format_profiles
from backend.app.domain.document import BoundingBox, DocumentLayout, TextBlock


PRODUCT_RE = re.compile(r"25BH2B\d{7}")


class Molino1Adapter:
    name = "MOLINO_1_BX_POSCO"

    def match(self, document: DocumentLayout) -> AdapterMatch:
        profile, score, signals = evaluate_format_profiles(document)
        return AdapterMatch(self.name, score if profile == self.name else 0.0, signals)

    def extract(self, document: DocumentLayout) -> dict[str, object]:
        page = document.pages[0]
        total_pieces = None
        if page.rotation == 0:
            for label in page.blocks:
                if "totalpieces" not in re.sub(r"\s+", "", label.text.lower()):
                    continue
                values = [block for block in page.blocks if re.fullmatch(r"\d+", block.text.strip()) and block.bbox.x0 >= label.bbox.x1 and block.bbox.x0 - label.bbox.x1 < page.width * .1 and abs((block.bbox.top + block.bbox.bottom - label.bbox.top - label.bbox.bottom) / 2) < 10]
                if values:
                    total_pieces = int(min(values, key=lambda block: block.bbox.x0).text.strip())
        if page.rotation == 0:
            # Keep this adapter's calibrated coordinates after ingestion supplies upright pages.
            page = replace(page, blocks=tuple(replace(block, bbox=BoundingBox(
                page.height - block.bbox.bottom, block.bbox.x0,
                page.height - block.bbox.top, block.bbox.x1,
            )) for block in page.blocks))
        product_blocks = sorted(
            (block for block in page.blocks if PRODUCT_RE.fullmatch(block.text.strip())),
            key=lambda block: block.bbox.x0,
            reverse=True,
        )
        if not product_blocks:
            raise ValueError("Molino 1 no contiene identificadores de rollo reconocibles")

        rows = [self._row(page.blocks, block, index) for index, block in enumerate(product_blocks, 1)]
        text = " ".join(block.text for block in page.blocks)
        certificate = self._first(r"E0\d{10}", text)
        delivery_date = self._first(r"20\d{6}", text)
        standard = self._first(r"BTA\s*BLZ112[^\n]*?PW\.T", text, flags=re.IGNORECASE)
        return {
            "document": {
                "source_name": document.file_name,
                "supplier": "BX Steel Posco Cold Rolled Sheet Co., Ltd.",
                "certificate_no": certificate,
                "product_name": "Cold-rolled steel strip",
                "delivery_date_raw": delivery_date,
            },
            "standard": standard,
            "rolling": "cold",
            "condition": ["annealed", "skin_passed"],
            "chemistry_scales": {
                "C": "10^-4", "Si": "10^-2", "Mn": "10^-2", "P": "10^-3",
                "S": "10^-3", "Als": "10^-3", "Ti": "10^-3",
            },
            "total_pieces": total_pieces,
            "total_net_weight_kg": sum(int(row["net_weight_kg"]) for row in rows),
            "total_gross_weight_kg": sum(int(row["gross_weight_kg"]) for row in rows),
            "rows": rows,
        }

    @classmethod
    def _row(
        cls, blocks: tuple[TextBlock, ...], product: TextBlock, row_number: int
    ) -> dict[str, object]:
        anchor = (product.bbox.x0 + product.bbox.x1) / 2
        value = lambda top, offset=0, pattern=r".+": cls._near(
            blocks, anchor + offset, top, pattern
        )
        return {
            "product_id": product.text.strip(),
            "heat_no": value(74, -8, r"\d{7}"),
            "thickness_mm": value(108, 0, r"\d+(?:\.\d+)?"),
            "width_mm": value(127, 0, r"\d+"),
            "length_raw": value(147, 0, r"C"),
            "net_weight_kg": value(173, 0, r"\d{4,5}"),
            "gross_weight_kg": value(173, -8, r"\d{4,5}"),
            "chemistry": {
                "C": value(237, 0, r"\d+"), "Si": value(256, 0, r"\d+"),
                "Mn": value(275, 0, r"\d+"), "P": value(294, 0, r"\d+"),
                "S": value(314, 0, r"\d+"), "Als": value(334, 0, r"\d+"),
                "Ti": value(355, 0, r"\d+"),
            },
            "yield_strength_mpa": value(445, -8, r"\d+"),
            "tensile_strength_mpa": value(464, 0, r"\d+"),
            "elongation_pct": value(484, 0, r"\d+(?:\.\d+)?"),
            "evidence": [{"page": product.page_number, "region": f"product_table_row_{row_number}"}],
        }

    @staticmethod
    def _near(
        blocks: tuple[TextBlock, ...], x: float, top: float, pattern: str
    ) -> str:
        regex = re.compile(pattern)
        matches = [
            block for block in blocks
            if abs(((block.bbox.x0 + block.bbox.x1) / 2) - x) <= 5
            and abs(((block.bbox.top + block.bbox.bottom) / 2) - top) <= 8
            and regex.fullmatch(block.text.strip())
        ]
        if not matches:
            raise ValueError(f"Molino 1: falta valor cerca de columna {top} y fila {x:.1f}")
        return min(matches, key=lambda block: abs(((block.bbox.top + block.bbox.bottom) / 2) - top)).text.strip()

    @staticmethod
    def _first(pattern: str, text: str, *, flags: int = 0) -> str | None:
        match = re.search(pattern, text, flags)
        return " ".join(match.group(0).split()) if match else None
