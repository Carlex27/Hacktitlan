"""Coverage matrix and status mapping for Chapter 72 tariff branches."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import json
from pathlib import Path
from typing import Any

from backend.app.classification_engine.catalog import DEFAULT_CATALOG_PATH, compact_code

FLAT_ROLLED_HEADINGS = {
    "7208", "7209", "7210", "7211", "7212", "7219", "7220", "7225", "7226"
}

# Fractions returned by an executable branch in engine.py. Coverage must never
# infer implementation merely from the heading prefix.
EXECUTABLE_FRACTIONS = frozenset("""
72081003 72082502 72082601 72082701 72083601 72083701 72083801 72083901
72084002 72085104 72085201 72085301 72085401 72091504 72091601 72091701
72091801 72092501 72092601 72092701 72092801 72101101 72101204 72102001
72103002 72104101 72104999 72105003 72106101 72106999 72107002 72109099
72111301 72111491 72111999 72112303 72112999 72119099 72121003 72122003
72123003 72124004 72125001 72126004 72191101 72191202 72191301 72191401
72192101 72192201 72192301 72192401 72193101 72193202 72193301 72193502
72199099 72201101 72201201 72202003 72209099 72251101 72251999 72253091
72254091 72255091 72259101 72259201 72259999 72261101 72261999 72262001
72269107 72269206 72269999
""".split())

# Source anomaly documented in data/ligie/chapter-72/source-provided/SOURCE.md:
# Page 38 (under 7219.34) and Page 39 (under 7219.35) both list 7219.35.02 with different descriptions.
AMBIGUOUS_SOURCE_CODES = {"72193502"}

BLOCKED_MISSING_FACT_CODES = {
    # Magnetic silicon electrical steel requiring core loss (W/kg at 50/60 Hz and 1.5 T):
    "72251101", "72251999", "72261101", "72261999",
    # Specific commercial end-use and secondary reduction (e.g. food can bodies / double cold reduction):
    "7210120401", "7210120402",
    # Automotive exposed body panels requiring deep-drawing stamping verification:
    "7209150403", "7225509110",
    # Cladding layer thickness ratio under Chapter Note 1(k):
    "72126004",
}


class BranchStatus(StrEnum):
    IMPLEMENTED = "implemented"
    BLOCKED_BY_MISSING_FACT = "blocked_by_missing_fact"
    AMBIGUOUS_SOURCE = "ambiguous_source"
    NOT_IMPLEMENTED = "not_implemented"
    OUT_OF_SCOPE = "out_of_scope"


@dataclass(frozen=True)
class CoverageEntry:
    code: str
    compact_code: str
    kind: str  # "heading", "fraction", "nico"
    status: BranchStatus
    heading: str
    description: str
    notes: str | None = None
    required_facts: tuple[str, ...] = ()


class Chapter72CoverageMatrix:
    """Matrix of coverage and classification feasibility for all Chapter 72 branches."""

    def __init__(self, catalog_path: Path = DEFAULT_CATALOG_PATH) -> None:
        self.catalog_path = catalog_path
        self._entries: list[CoverageEntry] = []
        self._by_code: dict[str, CoverageEntry] = {}
        self._load()

    def _load(self) -> None:
        raw = json.loads(self.catalog_path.read_text(encoding="utf-8"))
        for item in raw:
            item_type = str(item.get("type") or "")
            code_raw = str(item.get("code") or "")
            if not code_raw or item_type not in {"heading", "fraction", "nico"}:
                continue

            cleaned = compact_code(code_raw)
            heading_code = cleaned[:4]
            desc = str(item.get("description") or "")

            if heading_code not in FLAT_ROLLED_HEADINGS:
                status = BranchStatus.OUT_OF_SCOPE
                notes = "Producto siderúrgico no plano (fuera del alcance del motor de laminados planos)."
                required_facts = ()
            elif cleaned in AMBIGUOUS_SOURCE_CODES:
                status = BranchStatus.AMBIGUOUS_SOURCE
                notes = (
                    "Anomalía en la fuente original (PDF LIGIE SIN VIGENCIA páginas 38-39): "
                    "la fracción 7219.35.02 aparece duplicada con distintas descripciones."
                )
                required_facts = ("official_dof_resolution",)
            elif cleaned in BLOCKED_MISSING_FACT_CODES or any(
                len(blocked) == 8 and cleaned.startswith(blocked)
                for blocked in BLOCKED_MISSING_FACT_CODES
            ):
                status = BranchStatus.BLOCKED_BY_MISSING_FACT
                notes = "Requiere hechos externos al certificado de molino (ensayos de pérdida magnética o uso industrial final)."
                required_facts = self._determine_missing_facts(cleaned)
            elif (
                item_type == "heading"
                or cleaned[:8] in EXECUTABLE_FRACTIONS
            ):
                status = BranchStatus.IMPLEMENTED
                notes = "Regla determinista implementada sobre propiedades físicas y composición química."
                required_facts = self._determine_required_facts(cleaned)
            else:
                status = BranchStatus.NOT_IMPLEMENTED
                notes = "No existe una ruta ejecutable para esta rama arancelaria."
                required_facts = ("implemented_tariff_branch",)

            entry = CoverageEntry(
                code=code_raw,
                compact_code=cleaned,
                kind=item_type,
                status=status,
                heading=heading_code,
                description=desc,
                notes=notes,
                required_facts=required_facts,
            )
            self._entries.append(entry)
            # Store in lookup dict; if duplicate code, preserve ambiguous marker
            if cleaned not in self._by_code or status == BranchStatus.AMBIGUOUS_SOURCE:
                self._by_code[cleaned] = entry

    @staticmethod
    def _determine_missing_facts(code: str) -> tuple[str, ...]:
        if code.startswith(("722511", "722519", "722611", "722619")):
            return ("magnetic_loss_w_per_kg", "magnetic_induction_tesla")
        if code.startswith("72101204"):
            return ("secondary_reduction_ratio", "can_body_end_use")
        if code in {"7209150403", "7225509110"}:
            return ("porcelain_exposed_parts", "deep_drawing_class")
        if code == "72126004":
            return ("cladding_weight_percentage",)
        return ("external_commercial_fact",)

    @staticmethod
    def _determine_required_facts(code: str) -> tuple[str, ...]:
        facts = ["width_mm", "thickness_mm", "coiled", "rolling"]
        if code.startswith(("7210", "7212", "722591", "722592", "722599")):
            facts.append("coating")
        if code.startswith(("7219", "7220")):
            facts.append("stainless_chemistry")
        elif code.startswith(("7225", "7226")):
            facts.append("alloy_chemistry")
        else:
            facts.append("non_alloy_chemistry")
        return tuple(facts)

    @property
    def entries(self) -> tuple[CoverageEntry, ...]:
        return tuple(self._entries)

    def get(self, code: str) -> CoverageEntry | None:
        cleaned = compact_code(code)
        return self._by_code.get(cleaned)

    def summary(self) -> dict[str, Any]:
        counts_by_status = {status.value: 0 for status in BranchStatus}
        counts_by_kind = {"heading": 0, "fraction": 0, "nico": 0}
        for entry in self._entries:
            counts_by_status[entry.status.value] += 1
            counts_by_kind[entry.kind] = counts_by_kind.get(entry.kind, 0) + 1

        flat_counts = {status.value: 0 for status in BranchStatus}
        for entry in self._entries:
            if entry.heading in FLAT_ROLLED_HEADINGS:
                flat_counts[entry.status.value] += 1

        return {
            "total_catalog_entries": len(self._entries),
            "by_kind": counts_by_kind,
            "overall_by_status": counts_by_status,
            "flat_rolled_scope_by_status": flat_counts,
            "flat_rolled_headings": sorted(FLAT_ROLLED_HEADINGS),
        }


def get_coverage_matrix() -> Chapter72CoverageMatrix:
    return Chapter72CoverageMatrix()
