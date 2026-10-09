"""Explicit dimensional units; internal thickness/width are mm, length is m."""

import re
from decimal import Decimal
from fractions import Fraction


def dimension_unit(text: str) -> str | None:
    for unit, pattern in (
        ("mm", r"\bmm\b|mil[ií]metros?"),
        ("cm", r"\bcm\b|cent[ií]metros?"),
        ("in", r'\bin(?:ch(?:es)?)?\b|pulgadas?|["″]'),
        ("ft", r"\b(?:ft|feet|foot|pies?|pie)\b|['′]"),
        ("m", r"\bm\b|\bmetros?\b"),
    ):
        if re.search(pattern, text, re.I):
            return unit
    return None


def dimension_value(text: str, header: str, *, length: bool = False) -> float | None:
    unit = dimension_unit(text) or dimension_unit(header) or ("m" if length else "mm")
    # Reject unknown suffixes instead of stripping them into an assumed unit.
    match = re.fullmatch(
        r'\s*((?:\d+(?:[.,]\d+)?|[.,]\d+)(?:\s+\d+/\d+)?|\d+/\d+)\s*'
        r'(mm|cm|m|in|inch|inches|ft|feet|foot|pulgadas?|pies?|mil[ií]metros?|cent[ií]metros?|metros?|["″\x27′])?\s*',
        text, re.I,
    )
    if not match:
        return None
    try:
        parts = match.group(1).replace(",", ".").split()
        value = sum((Fraction(part) for part in parts), Fraction())
        numeric = Decimal(value.numerator) / Decimal(value.denominator)
        factor = {"mm": Decimal(1), "cm": Decimal(10), "m": Decimal(1000), "in": Decimal("25.4"), "ft": Decimal("304.8")}[unit]
        return float(numeric * factor / (Decimal(1000) if length else Decimal(1)))
    except (ValueError, ZeroDivisionError):
        return None
