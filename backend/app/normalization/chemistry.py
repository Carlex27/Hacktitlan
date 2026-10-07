"""Exact normalization rules for chemical composition observations."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
import re


class ChemistryNormalizationError(ValueError):
    """Raised when a chemistry observation cannot be normalized safely."""


_SUPERSCRIPT_TRANSLATION = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹⁻⁺", "0123456789-+")


def parse_power_of_ten(value: int | str) -> int:
    """Return the exponent from values such as ``-4``, ``10^-4`` or ``10⁻⁴``."""

    if isinstance(value, bool):
        raise ChemistryNormalizationError("A boolean is not a valid exponent")
    if isinstance(value, int):
        return value

    compact = str(value).strip().translate(_SUPERSCRIPT_TRANSLATION)
    compact = re.sub(r"\s+", "", compact)
    match = re.fullmatch(r"(?:10(?:\^)?(?:\((-?\d+)\)|(-?\d+))|(-?\d+))", compact)
    if not match:
        raise ChemistryNormalizationError(f"Unsupported power-of-ten notation: {value!r}")
    return int(next(group for group in match.groups() if group is not None))


def _to_decimal(value: int | float | str | Decimal) -> Decimal:
    if isinstance(value, bool):
        raise ChemistryNormalizationError("A boolean is not a chemical value")
    if isinstance(value, Decimal):
        return value
    text = str(value).strip().replace(" ", "")
    if not text:
        raise ChemistryNormalizationError("An empty cell is unknown, not zero")
    if "," in text and "." not in text:
        text = text.replace(",", ".")
    try:
        return Decimal(text)
    except InvalidOperation as exc:
        raise ChemistryNormalizationError(f"Invalid chemical value: {value!r}") from exc


def normalize_scaled_percentage(
    raw_value: int | float | str | Decimal | None,
    scale: int | str,
) -> Decimal | None:
    """Normalize a table cell to percent using its column exponent.

    The certificate's header is authoritative: ``13`` under ``C 10^-4`` is
    ``13 * 10^-4 = 0.0013 %``. A missing value remains ``None``; only an
    explicit zero becomes ``0 %``.
    """

    if raw_value is None:
        return None
    exponent = parse_power_of_ten(scale)
    result = _to_decimal(raw_value) * (Decimal(10) ** exponent)
    if result < 0 or result > 100:
        raise ChemistryNormalizationError(
            f"Normalized percentage {result} is outside the physical range 0..100"
        )
    return result
