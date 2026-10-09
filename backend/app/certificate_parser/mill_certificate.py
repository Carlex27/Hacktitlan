"""Format-independent certificate normalization after OCR/table extraction.

This module deliberately does not perform tariff classification. It accepts a
small intermediate representation that any supplier-specific adapter or OCR
engine can produce and returns the canonical product observations.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from backend.app.normalization.chemistry import normalize_scaled_percentage


class CertificateParseError(ValueError):
    """Raised when extracted certificate data is contradictory or incomplete."""


ELEMENT_ALIASES = {
    "c": "C",
    "carbon": "C",
    "碳": "C",
    "si": "Si",
    "silicon": "Si",
    "硅": "Si",
    "mn": "Mn",
    "manganese": "Mn",
    "锰": "Mn",
    "p": "P",
    "phosphorus": "P",
    "磷": "P",
    "s": "S",
    "sulfur": "S",
    "硫": "S",
    # Als is acid-soluble aluminium. Do not silently merge it with total Al.
    "als": "Al_soluble",
    "solubleal": "Al_soluble",
    # Alt is total aluminium and has a different metallurgical meaning.
    "alt": "Al_total",
    "totalal": "Al_total",
    "ti": "Ti",
    "titanium": "Ti",
    "钛": "Ti",
    "al": "Al_total",
    "cu": "Cu",
    "ni": "Ni",
    "cr": "Cr",
    "b": "B",
    "mo": "Mo",
    "n": "N",
}

DITTO_MARKS = {'"', "''", "〃", "同上"}


def _decimal(value: Any, field: str) -> Decimal:
    try:
        return Decimal(str(value).strip())
    except Exception as exc:
        raise CertificateParseError(f"Invalid numeric value for {field}: {value!r}") from exc


def _element_key(label: str) -> str:
    compact = "".join(str(label).strip().lower().split())
    return ELEMENT_ALIASES.get(compact, str(label).strip())


def _json_number(value: Decimal | None) -> float | None:
    return None if value is None else float(value)


def _is_ditto(value: Any) -> bool:
    return isinstance(value, str) and value.strip() in DITTO_MARKS


def _resolve_ditto(value: Any, previous: Any, field: str, row_number: int) -> Any:
    if not _is_ditto(value):
        return value
    if previous in (None, ""):
        raise CertificateParseError(
            f"Row {row_number} uses a ditto mark for {field} without a previous value"
        )
    return previous


def _optional_number(row: dict[str, Any], key: str) -> float | None:
    value = row.get(key)
    return None if value in (None, "") else _json_number(_decimal(value, key))


def normalize_certificate(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalize an OCR-neutral mill-certificate payload and validate totals."""

    scales = raw.get("chemistry_scales") or {}
    rows = raw.get("rows") or []
    if not rows:
        raise CertificateParseError("The certificate contains no product rows")

    normalized_scales = {_element_key(k): v for k, v in scales.items()}
    products: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    previous_row: dict[str, Any] = {}
    previous_chemistry: dict[str, Any] = {}

    for index, row in enumerate(rows, start=1):
        original_row = dict(row)
        row = dict(original_row)
        row_scales = {**normalized_scales, **{_element_key(k): v for k, v in (row.get("chemistry_scales") or {}).items()}}
        previous_product_id = products[-1]["product_id"] if products else None
        for field in (
            "heat_no",
            "thickness_mm",
            "width_mm",
            "length_raw",
            "quantity",
        ):
            row[field] = _resolve_ditto(row.get(field), previous_row.get(field), field, index)

        product_id = str(row.get("product_id") or "").strip()
        if not product_id:
            raise CertificateParseError(f"Row {index} has no product/coil identifier")
        if product_id in seen_ids:
            raise CertificateParseError(f"Duplicate product identifier: {product_id}")
        seen_ids.add(product_id)

        chemistry: dict[str, float | None] = {}
        chemistry_observations: dict[str, dict[str, Any]] = {}
        original_chemistry = dict(original_row.get("chemistry") or {})
        chemistry_raw = dict(original_chemistry)
        for source_label, source_raw_value in original_chemistry.items():
            inherited = _is_ditto(source_raw_value)
            raw_value = source_raw_value
            raw_value = _resolve_ditto(
                raw_value,
                previous_chemistry.get(source_label),
                f"chemistry.{source_label}",
                index,
            )
            element = _element_key(source_label)
            if element not in row_scales:
                raise CertificateParseError(
                    f"No exponent was extracted for chemistry column {source_label!r}"
                )
            normalized_percentage = _json_number(
                normalize_scaled_percentage(raw_value, row_scales[element])
            )
            chemistry[element] = normalized_percentage
            chemistry_observations[element] = {
                "source_label": source_label,
                "raw_value": source_raw_value,
                "normalized_value": normalized_percentage,
                "unit": "%",
                "inherited": inherited,
                "inherited_from": previous_product_id if inherited else None,
            }
            chemistry_raw[source_label] = raw_value

        length_raw = row.get("length_raw")
        if length_raw in (None, "") and row.get("length_m") is not None:
            length_raw = row.get("length_m")
        coiled = str(length_raw).strip().upper() in {"C", "COIL", "COILED", "ROLLO"}
        quantity = int(row.get("quantity") or 1)
        if quantity < 1:
            raise CertificateParseError(f"Row {index} has an invalid quantity: {quantity}")
        width_mm = _optional_number(row, "width_mm")
        thickness_mm = _optional_number(row, "thickness_mm")
        length_m = (
            None
            if coiled or length_raw in (None, "")
            else _json_number(_decimal(length_raw, "length_m"))
        )
        field_observations = {
            "thickness_mm": {
                "raw_value": original_row.get("thickness_mm"),
                "normalized_value": thickness_mm,
                "unit": "mm" if thickness_mm is not None else None,
                "inherited": _is_ditto(original_row.get("thickness_mm")),
                "inherited_from": previous_product_id
                if _is_ditto(original_row.get("thickness_mm"))
                else None,
            },
            "width_mm": {
                "raw_value": original_row.get("width_mm"),
                "normalized_value": width_mm,
                "unit": "mm" if width_mm is not None else None,
                "inherited": _is_ditto(original_row.get("width_mm")),
                "inherited_from": previous_product_id
                if _is_ditto(original_row.get("width_mm"))
                else None,
            },
            "length": {
                "raw_value": original_row.get("length_raw"),
                "normalized_value": "coiled" if coiled else length_m,
                "unit": None if coiled else "m",
                "inherited": _is_ditto(original_row.get("length_raw")),
                "inherited_from": previous_product_id
                if _is_ditto(original_row.get("length_raw"))
                else None,
            },
        }
        products.append(
            {
                "product_id": product_id,
                "label_no": row.get("label_no"),
                "heat_no": row.get("heat_no"),
                "quantity": quantity,
                "composition_pct": chemistry,
                "form": "flat_rolled",
                "coiled": coiled,
                "rolling": raw.get("rolling"),
                "condition": raw.get("condition"),
                "width_mm": width_mm,
                "thickness_mm": thickness_mm,
                "length_m": length_m,
                "weight_kg": _optional_number(row, "weight_kg"),
                "weight_kind": row.get("weight_kind"),
                "net_weight_kg": _optional_number(row, "net_weight_kg"),
                "gross_weight_kg": _optional_number(row, "gross_weight_kg"),
                "mechanical_properties": {
                    key: _json_number(_decimal(row[key], key))
                    for key in (
                        "yield_strength_mpa",
                        "tensile_strength_mpa",
                        "elongation_pct",
                        "n_value",
                        "r_value",
                        "hardness_hrb",
                    )
                    if row.get(key) not in (None, "")
                },
                "coating": {
                    "metal": row.get("coating_metal") or (raw.get("coating") or {}).get("metal"),
                    "process": (raw.get("coating") or {}).get("process"),
                    "superior_g_m2": _optional_number(row, "coating_superior_g_m2"),
                    "inferior_g_m2": _optional_number(row, "coating_inferior_g_m2"),
                    "post_treatment": (raw.get("coating") or {}).get("post_treatment"),
                },
                "sample_position": row.get("sample_position"),
                "bend_test": row.get("bend_test"),
                "chemistry_analysis_type": row.get("chemistry_analysis_type")
                or raw.get("chemistry_analysis_type"),
                "standard": raw.get("standard"),
                "edge_condition": raw.get("edge_condition"),
                "observations": {
                    **field_observations,
                    "composition_pct": chemistry_observations,
                },
                "evidence": row.get("evidence", []),
            }
        )
        previous_row = row
        previous_chemistry = chemistry_raw

    expected_count = raw.get("total_pieces")
    observed_count = sum(product["quantity"] for product in products)
    if expected_count is not None and int(expected_count) != observed_count:
        raise CertificateParseError(
            f"Piece count {observed_count} does not match total pieces {expected_count}"
        )

    checks: dict[str, bool] = {"piece_count_matches": expected_count is None or int(expected_count) == observed_count}
    for source_key, product_key, check_key in (
        ("total_weight_kg", "weight_kg", "weight_matches"),
        ("total_net_weight_kg", "net_weight_kg", "net_weight_matches"),
        ("total_gross_weight_kg", "gross_weight_kg", "gross_weight_matches"),
    ):
        expected = raw.get(source_key)
        if expected is not None:
            if any(product[product_key] is None for product in products):
                raise CertificateParseError(
                    f"{source_key} is present but one or more rows have no {product_key}"
                )
            observed = sum(Decimal(str(product[product_key])) for product in products)
            checks[check_key] = observed == _decimal(expected, source_key)
            if not checks[check_key]:
                raise CertificateParseError(
                    f"{source_key}={expected} does not match row sum {observed}"
                )

    for subtotal in raw.get("subtotals") or []:
        match_field = subtotal["match_field"]
        match_value = subtotal["match_value"]
        group = [product for product in products if product.get(match_field) == match_value]
        if not group:
            raise CertificateParseError(
                f"Subtotal group {match_field}={match_value!r} has no matching products"
            )
        if subtotal.get("total_pieces") is not None:
            group_pieces = sum(product["quantity"] for product in group)
            if group_pieces != int(subtotal["total_pieces"]):
                raise CertificateParseError(
                    f"Subtotal {match_field}={match_value!r} pieces "
                    f"{group_pieces} != {subtotal['total_pieces']}"
                )
        if subtotal.get("total_weight_kg") is not None:
            if any(product["weight_kg"] is None for product in group):
                raise CertificateParseError(
                    f"Subtotal {match_field}={match_value!r} has missing weights"
                )
            group_weight = sum(Decimal(str(product["weight_kg"])) for product in group)
            if group_weight != _decimal(subtotal["total_weight_kg"], "subtotal.total_weight_kg"):
                raise CertificateParseError(
                    f"Subtotal {match_field}={match_value!r} weight "
                    f"{group_weight} != {subtotal['total_weight_kg']}"
                )
    if raw.get("subtotals"):
        checks["subtotals_match"] = True

    return {
        "document": raw.get("document", {}),
        "standard": raw.get("standard"),
        "products": products,
        "validation": checks,
    }
