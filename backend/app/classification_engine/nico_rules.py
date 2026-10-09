"""NICO conditions verified against the supplied PDF; unknown is never matched."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from .models import ProductFacts, StepOutcome

Value = Decimal | str | bool | None
Operator = Literal["=", "<", "<=", ">", ">="]


@dataclass(frozen=True)
class Condition:
    field: str
    operator: Operator
    value: str | bool

    def evaluate(self, facts: ProductFacts) -> bool | None:
        observed = observation(facts, self.field)
        if observed is None:
            return None
        expected = Decimal(self.value) if isinstance(observed, Decimal) else self.value
        if self.operator == "=":
            return observed == expected
        if not isinstance(observed, Decimal) or not isinstance(expected, Decimal):
            return False
        return {
            "<": observed < expected,
            "<=": observed <= expected,
            ">": observed > expected,
            ">=": observed >= expected,
        }[self.operator]


def observation(facts: ProductFacts, field: str) -> Value:
    if field.startswith("composition_pct."):
        return facts.composition_pct.get(field.split(".", 1)[1])
    name = field.removeprefix("mechanical_properties.")
    # shortcut: product_kind/porcelain_steel need audited capture before resolving their NICO.
    return getattr(facts, name, None)


def conditions_for(fraction: str, nico: str) -> tuple[Condition, ...] | None:
    """None means unverified; () means a single, unconditional NICO 00."""
    c = Condition
    if fraction == "72255091":
        boron = (c("composition_pct.B", ">=", "0.0008"), c("tool_steel", "=", False))
        dimensions = {
            "01": (c("coiled", "=", True), c("thickness_mm", ">", "1"), c("thickness_mm", "<", "3")),
            "02": (c("coiled", "=", True), c("thickness_mm", ">=", "0.5"), c("thickness_mm", "<=", "1")),
            "03": (c("coiled", "=", True), c("thickness_mm", "<", "0.5")),
            "04": (c("coiled", "=", True), c("thickness_mm", ">=", "3"), c("thickness_mm", "<", "4.75")),
            "05": (c("coiled", "=", True), c("thickness_mm", ">=", "4.75")),
            "06": (c("coiled", "=", False), c("thickness_mm", "<", "4.75")),
            "07": (c("coiled", "=", False), c("thickness_mm", ">=", "4.75")),
        }
        if nico in dimensions:
            return boron + dimensions[nico]
        return {
            "08": (c("high_speed_steel", "=", True),),
            "09": (c("tool_steel", "=", True),),
            "10": (c("porcelain_steel", "=", True), c("thickness_mm", ">=", "4.75")),
            "11": (c("mechanical_properties.yield_strength_mpa", ">=", "355"),),
            "91": (c("thickness_mm", ">=", "4.75"),),
            "92": (c("porcelain_steel", "=", True), c("thickness_mm", "<", "4.75")),
        }.get(nico)
    if fraction in {"72104101", "72104199"} and nico == "00":
        return (c("pattern_in_relief", "=", True), c("coating_both_sides", "=", fraction == "72104101"))
    if fraction == "72103002" and nico in {"01", "99"}:
        return (c("coating_both_sides", "=", nico == "01"),)
    if fraction == "72104999":
        return {
            "01": (c("thickness_mm", "<", "3"), c("mechanical_properties.yield_strength_mpa", ">=", "275")),
            "02": (c("mechanical_properties.yield_strength_mpa", ">=", "355"),),
        }.get(nico)
    if fraction == "72191202":
        return {"01": (c("thickness_mm", "<=", "6"), c("width_mm", ">=", "710"), c("width_mm", "<=", "1350"))}.get(nico)
    if fraction == "72193101":
        return (c("coiled", "=", nico == "01"),) if nico in {"01", "99"} else None
    if fraction in {"72191301", "72191401", "72192201", "72193301"}:
        series = {"01": "200", "02": "300", "03": "400"}.get(nico)
        return (c("stainless_series", "=", series),) if series else None
    if fraction == "72193202":
        series = {"02": "200", "03": "300", "04": "400", "91": "200", "92": "300", "93": "400"}.get(nico)
        if series:
            return (c("stainless_series", "=", series), c("thickness_mm", ">" if nico in {"91", "92", "93"} else "<=", "4"))
        return None
    if fraction in {"72112303", "72112999"}:
        if nico == "01":
            return (c("product_kind", "=", "strip"), c("thickness_mm", ">=", "0.05")) + ((c("composition_pct.C", "<", "0.6"),) if fraction == "72112999" else ())
        if fraction == "72112999" and nico == "02":
            return (c("product_kind", "=", "strip"), c("composition_pct.C", ">=", "0.6"))
        if nico == ("02" if fraction == "72112303" else "03"):
            return (c("product_kind", "=", "sheet"), c("thickness_mm", ">", "0.46"), c("thickness_mm", "<=", "3.4"))
        return None
    if fraction == "72111491":
        return {
            "01": (c("product_kind", "=", "strip"), c("coiled", "=", False)),
            "02": (c("product_kind", "=", "sheet"), c("coiled", "=", False), c("thickness_mm", ">=", "4.75"), c("thickness_mm", "<", "12")),
            "03": (c("coiled", "=", True),),
        }.get(nico)
    if fraction == "72111999":
        return {
            "01": (c("product_kind", "=", "strip"), c("thickness_mm", "<", "4.75")),
            "02": (c("product_kind", "=", "sheet"), c("thickness_mm", ">=", "1.9"), c("thickness_mm", "<", "4.75")),
            "03": (c("product_kind", "=", "coil_stock"),),
            "04": (c("product_kind", "=", "sheet"), c("width_mm", ">", "500"), c("width_mm", "<", "600"), c("thickness_mm", ">=", "1.9"), c("thickness_mm", "<", "4.75")),
        }.get(nico)
    if fraction in {"72122003", "72123003"}:
        return {
            "01": (c("product_kind", "=", "strip"),),
            "02": (c("coating_both_sides", "=", True), c("width_mm", ">", "500")),
        }.get(nico)
    if fraction == "72121003":
        return {"01": (c("product_kind", "=", "strip"),), "02": (c("product_kind", "=", "sheet"),)}.get(nico)
    if fraction == "72259201":
        return {"01": (c("mechanical_properties.yield_strength_mpa", ">=", "355"),), "99": (c("mechanical_properties.yield_strength_mpa", "<", "355"),)}.get(nico)
    return None


def assess_conditions(facts: ProductFacts, conditions: tuple[Condition, ...]) -> StepOutcome:
    results = [condition.evaluate(facts) for condition in conditions]
    if False in results:
        return StepOutcome.CONFLICT
    if None in results:
        return StepOutcome.UNKNOWN
    return StepOutcome.MATCHED


def assessed_nico(facts: ProductFacts, fraction: str, nico: str) -> StepOutcome | None:
    conditions = conditions_for(fraction, nico)
    if fraction == "72255091" and nico in {"91", "92"}:
        assert conditions is not None
        base = assess_conditions(facts, conditions)
        if base is StepOutcome.CONFLICT:
            return base
        specific = [assessed_nico(facts, fraction, value) for value in ("01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11")]
        if StepOutcome.MATCHED in specific:
            return StepOutcome.CONFLICT
        return StepOutcome.MATCHED if base is StepOutcome.MATCHED and all(value is StepOutcome.CONFLICT for value in specific) else StepOutcome.UNKNOWN
    if conditions is not None:
        return assess_conditions(facts, conditions)
    if fraction == "72255091" and nico == "99":
        specifics = [assessed_nico(facts, fraction, value) for value in ("01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "91", "92")]
        if StepOutcome.MATCHED in specifics:
            return StepOutcome.CONFLICT
        return StepOutcome.MATCHED if all(value is StepOutcome.CONFLICT for value in specifics) else StepOutcome.UNKNOWN
    # Residual categories require exclusion of every specific NICO.
    if fraction == "72104999" and nico == "99":
        first = assessed_nico(facts, fraction, "01")
        second = assessed_nico(facts, fraction, "02")
        if StepOutcome.MATCHED in (first, second):
            return StepOutcome.CONFLICT
        return StepOutcome.MATCHED if first == second == StepOutcome.CONFLICT else StepOutcome.UNKNOWN
    if fraction == "72191202" and nico == "99":
        specific = assessed_nico(facts, fraction, "01")
        return {StepOutcome.MATCHED: StepOutcome.CONFLICT, StepOutcome.CONFLICT: StepOutcome.MATCHED}.get(specific, StepOutcome.UNKNOWN)
    if fraction in {"72191301", "72191401", "72192201", "72193202", "72193301"} and nico == "99":
        if facts.stainless_series is None:
            return StepOutcome.UNKNOWN
        return StepOutcome.CONFLICT if facts.stainless_series in {"200", "300", "400"} else StepOutcome.MATCHED
    return None
