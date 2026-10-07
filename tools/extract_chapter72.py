"""Extract Chapter 72 tariff rows from the supplied unified LIGIE PDF.

This produces a faithful source-derived catalog. It does not assert that the
source PDF is legally current; validity is tracked separately in SOURCE.md.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path
from typing import Any

import pdfplumber


ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path(r"C:\Users\ofici\Downloads\LIGIE-UNIFICADA-ACERO.pdf")
OUTPUT = ROOT / "data" / "ligie" / "chapter-72" / "source-provided"

HEADING_RE = re.compile(r"^72\.\d{2}$")
SUBHEADING_RE = re.compile(r"^\d{4}\.\d{2}$")
FRACTION_RE = re.compile(r"^\d{4}\.\d{2}\.\d{2}$")
NICO_RE = re.compile(r"^\d{2}$")


def clean(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    raw_rows: list[dict[str, Any]] = []
    catalog: list[dict[str, Any]] = []
    current_heading = ""
    current_subheading = ""
    current_fraction = ""

    with pdfplumber.open(SOURCE) as pdf:
        metadata = dict(pdf.metadata or {})

        # Chapter 72 tariff tables begin on PDF page 12. Page 50 ends Chapter
        # 72 and then starts Chapter 73; the table extraction captures only the
        # Chapter 72 table at the top of that page.
        for page_number in range(12, 51):
            page = pdf.pages[page_number - 1]
            tables = page.extract_tables(
                {
                    "vertical_strategy": "lines",
                    "horizontal_strategy": "lines",
                    "snap_tolerance": 3,
                    "join_tolerance": 3,
                }
            )
            candidates = [table for table in tables if table and max(len(row) for row in table) >= 4]
            if not candidates:
                continue
            table = max(candidates, key=len)

            for row_number, row in enumerate(table, start=1):
                cells = [clean(cell) for cell in row]
                cells.extend([""] * (11 - len(cells)))
                code, marker, description = cells[0], cells[1], cells[2]

                raw_rows.append(
                    {
                        "page": page_number,
                        "row": row_number,
                        "code": code,
                        "nico_or_subpart": marker,
                        "description": description,
                        "umt": cells[3],
                        "import_tax": cells[4],
                        "export_tax": cells[7],
                        "regulations_programs": cells[10],
                        "cells": cells,
                    }
                )

                if code == "CÓDIGO" or description in {"DESCRIPCIÓN", ""}:
                    continue

                base = {
                    "page": page_number,
                    "description": description,
                    "umt": cells[3],
                    "import_tax": cells[4],
                    "export_tax": cells[7],
                    "regulations_programs": cells[10],
                }

                if HEADING_RE.fullmatch(code):
                    current_heading = code
                    current_subheading = ""
                    current_fraction = ""
                    catalog.append({**base, "type": "heading", "code": code, "parent": "72"})
                    continue

                if SUBHEADING_RE.fullmatch(code):
                    current_subheading = code
                    current_fraction = ""
                    parent = f"{code[:2]}.{code[2:4]}"
                    catalog.append({**base, "type": "subheading", "code": code, "parent": parent, "marker": marker})
                    continue

                if FRACTION_RE.fullmatch(code):
                    current_fraction = code
                    parent = code[:7]
                    catalog.append(
                        {
                            **base,
                            "type": "fraction",
                            "code": code,
                            "parent": parent,
                            "table_context_subheading": current_subheading,
                        }
                    )
                    if NICO_RE.fullmatch(marker):
                        catalog.append(
                            {
                                **base,
                                "type": "nico",
                                "code": f"{code}-{marker}",
                                "fraction": code,
                                "nico": marker,
                                "parent": code,
                            }
                        )
                    continue

                if not code and NICO_RE.fullmatch(marker) and current_fraction:
                    catalog.append(
                        {
                            **base,
                            "type": "nico",
                            "code": f"{current_fraction}-{marker}",
                            "fraction": current_fraction,
                            "nico": marker,
                            "parent": current_fraction,
                        }
                    )
                    continue

                if description and description not in {
                    "CUOTA (ARANCEL)",
                    "IMPUESTO DE IMP.",
                    "IMPUESTO DE EXP.",
                }:
                    parent = current_fraction or current_subheading or current_heading or "72"
                    catalog.append(
                        {
                            **base,
                            "type": "qualifier" if marker in {"-", "--", "---"} else "section",
                            "code": "",
                            "parent": parent,
                            "marker": marker,
                        }
                    )

        notes = []
        for page_number in range(5, 12):
            text = pdf.pages[page_number - 1].extract_text(layout=True) or ""
            notes.append(f"===== PDF PAGE {page_number} =====\n{text.rstrip()}")

    fractions = [item for item in catalog if item["type"] == "fraction"]
    nicos = [item for item in catalog if item["type"] == "nico"]
    duplicates = sorted(
        code for code in {item["code"] for item in nicos} if sum(row["code"] == code for row in nicos) > 1
    )
    duplicate_fractions = sorted(
        code
        for code in {item["code"] for item in fractions}
        if sum(row["code"] == code for row in fractions) > 1
    )
    orphan_nicos = sorted(item["code"] for item in nicos if not item.get("fraction"))
    hierarchy_mismatches = [
        {
            "fraction": item["code"],
            "expected_parent_from_code": item["parent"],
            "table_context_subheading": item["table_context_subheading"],
            "page": item["page"],
        }
        for item in fractions
        if item["table_context_subheading"] and item["parent"] != item["table_context_subheading"]
    ]

    (OUTPUT / "catalog.json").write_text(
        json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (OUTPUT / "raw-table-rows.json").write_text(
        json.dumps(raw_rows, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (OUTPUT / "notes-pages-5-11.txt").write_text("\n\n".join(notes) + "\n", encoding="utf-8")

    csv_fields = [
        "type",
        "code",
        "fraction",
        "nico",
        "parent",
        "description",
        "umt",
        "import_tax",
        "export_tax",
        "regulations_programs",
        "marker",
        "table_context_subheading",
        "page",
    ]
    with (OUTPUT / "catalog.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=csv_fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(catalog)

    report = {
        "source": str(SOURCE),
        "source_sha256": sha256(SOURCE),
        "pdf_metadata": metadata,
        "pages_processed": list(range(5, 51)),
        "table_pages": list(range(12, 51)),
        "counts": {
            "raw_rows": len(raw_rows),
            "catalog_records": len(catalog),
            "headings": sum(item["type"] == "heading" for item in catalog),
            "subheadings": sum(item["type"] == "subheading" for item in catalog),
            "fractions": len(fractions),
            "nicos": len(nicos),
            "qualifiers": sum(item["type"] == "qualifier" for item in catalog),
            "sections": sum(item["type"] == "section" for item in catalog),
        },
        "checks": {
            "duplicate_fraction_codes": duplicate_fractions,
            "duplicate_nico_codes": duplicates,
            "orphan_nicos": orphan_nicos,
            "fraction_hierarchy_mismatches": hierarchy_mismatches,
            "all_fraction_codes_begin_72": all(item["code"].startswith("72") for item in fractions),
            "all_nicos_have_two_digits": all(re.fullmatch(r"\d{2}", item["nico"]) for item in nicos),
        },
        "legal_status": "unverified; source PDF is visibly marked SIN VIGENCIA",
    }
    (OUTPUT / "qa-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
