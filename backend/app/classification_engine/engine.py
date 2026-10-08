from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from typing import Iterable

from backend.app.classification_engine.catalog import SourceProvidedCatalog
from backend.app.classification_engine.models import (
    ClassificationCandidate,
    ClassificationDecision,
    ClassificationOutcome,
    Decision,
    ProductFacts,
    StepOutcome,
)


ALLOY_THRESHOLDS = {
    "Al_total": Decimal("0.3"),
    "B": Decimal("0.0008"),
    "Cr": Decimal("0.3"),
    "Co": Decimal("0.3"),
    "Cu": Decimal("0.4"),
    "Pb": Decimal("0.4"),
    "Mn": Decimal("1.65"),
    "Mo": Decimal("0.08"),
    "Ni": Decimal("0.3"),
    "Nb": Decimal("0.06"),
    "Si": Decimal("0.6"),
    "Ti": Decimal("0.05"),
    "W": Decimal("0.3"),
    "V": Decimal("0.1"),
    "Zr": Decimal("0.05"),
    "OtherIndividual": Decimal("0.1"),
}


class Chapter72ClassificationEngine:
    """Conservative deterministic rules from the source-provided chapter 72.

    Missing chemistry is never treated as zero. The engine may determine a
    fraction while leaving NICO unresolved, and records every evaluated branch.
    """

    def __init__(self, catalog: SourceProvidedCatalog | None = None) -> None:
        self.catalog = catalog or SourceProvidedCatalog()

    def classify(self, facts: ProductFacts) -> ClassificationDecision:
        steps: list[Decision] = []
        missing: set[str] = set()
        if facts.form != "flat_rolled":
            steps.append(Decision(
                "chapter72.form.flat_rolled",
                StepOutcome.NOT_MATCHED,
                "El hito actual sólo cubre productos laminados planos.",
                {"form": facts.form},
                evidence_fields=("form",),
            ))
            return self._result(
                ClassificationOutcome.OUT_OF_SCOPE, None, None, None,
                missing, (), steps, facts,
            )

        for name, value in (
            ("width_mm", facts.width_mm),
            ("thickness_mm", facts.thickness_mm),
            ("coiled", facts.coiled),
            ("rolling", facts.rolling),
        ):
            if value is None:
                missing.add(name)
        if missing:
            steps.append(Decision(
                "chapter72.flat_rolled.required_dimensions",
                StepOutcome.MISSING,
                "Faltan propiedades físicas obligatorias para elegir la partida.",
                {"missing": sorted(missing)},
            ))
            return self._result(
                ClassificationOutcome.NEEDS_REVIEW, "flat_rolled", None, None,
                missing, (), steps, facts,
            )

        family, family_missing, family_candidates, family_steps = self._steel_family(facts)
        steps.extend(family_steps)
        missing.update(family_missing)
        if family is None:
            heading_candidates = self._heading_candidates(facts, family_candidates)
            return self._result(
                ClassificationOutcome.NEEDS_REVIEW,
                "flat_rolled",
                None,
                None,
                missing,
                heading_candidates,
                steps,
                facts,
            )

        if facts.coated is None:
            missing.add("coated")
            headings = tuple(dict.fromkeys(
                heading
                for coated in (False, True)
                if (heading := self._heading(replace(facts, coated=coated), family))
            ))
            steps.append(Decision(
                "chapter72.flat_rolled.coating_state",
                StepOutcome.MISSING,
                "La ausencia de un metal de recubrimiento no demuestra que el producto esté sin revestir.",
                evidence_fields=("coated",),
            ))
            return self._result(
                ClassificationOutcome.NEEDS_REVIEW,
                f"flat_rolled_{family}",
                None,
                None,
                missing,
                headings,
                steps,
                facts,
            )
        if facts.coated is False and facts.coating_metal:
            missing.add("coating_state_conflict")
            steps.append(Decision(
                "chapter72.flat_rolled.coating_state",
                StepOutcome.AMBIGUOUS,
                "El producto está marcado sin revestir pero también contiene un metal de recubrimiento.",
                {"coating_metal": facts.coating_metal},
                evidence_fields=("coated", "coating.metal"),
            ))
            return self._result(
                ClassificationOutcome.NEEDS_REVIEW,
                f"flat_rolled_{family}",
                None,
                None,
                missing,
                (),
                steps,
                facts,
            )

        fraction, nico, branch_missing, candidates, branch_steps = self._flat_rolled_branch(
            facts, family
        )
        steps.extend(branch_steps)
        missing.update(branch_missing)
        if fraction is not None:
            result_inputs, result_fields = self._classification_result_evidence(
                facts, fraction, nico
            )
            steps.append(Decision(
                "chapter72.classification.result",
                StepOutcome.MATCHED if nico is not None else StepOutcome.MISSING,
                (
                    f"Resultado candidato {fraction}-{nico}."
                    if nico is not None
                    else f"La fracción {fraction} requiere resolver el NICO."
                ),
                result_inputs,
                evidence_fields=result_fields,
            ))
        if fraction is not None:
            try:
                self.catalog.validate_result(fraction, nico)
            except ValueError as exc:
                missing.add("source_catalog_resolution")
                candidates = tuple(dict.fromkeys((*candidates, fraction)))
                steps.append(Decision(
                    "chapter72.source_catalog.validation",
                    StepOutcome.AMBIGUOUS,
                    str(exc),
                    {"fraction": fraction, "nico": nico},
                ))
                nico = None
        outcome = (
            ClassificationOutcome.CLASSIFIED
            if fraction is not None and nico is not None and not missing
            else ClassificationOutcome.NEEDS_REVIEW
        )
        return self._result(
            outcome,
            f"flat_rolled_{family}",
            fraction,
            nico,
            missing,
            candidates,
            steps,
            facts,
        )

    @staticmethod
    def _classification_result_evidence(
        facts: ProductFacts,
        fraction: str,
        nico: str | None,
    ) -> tuple[dict[str, object], tuple[str, ...]]:
        inputs: dict[str, object] = {
            "fraction": fraction,
            "nico": nico,
            "thickness_mm": str(facts.thickness_mm),
        }
        fields = ["thickness_mm"]
        if fraction == "72091504":
            carbon = facts.composition_pct.get("C")
            inputs["C"] = str(carbon) if carbon is not None else None
            inputs["yield_strength_mpa"] = (
                str(facts.yield_strength_mpa)
                if facts.yield_strength_mpa is not None else None
            )
            inputs["porcelain_exposed_parts"] = facts.porcelain_exposed_parts
            fields.extend((
                "composition_pct.C",
                "mechanical_properties.yield_strength_mpa",
                "porcelain_exposed_parts",
            ))
        elif fraction in {"72091601", "72091701", "72082601", "72082701", "72083801", "72083901"}:
            inputs["yield_strength_mpa"] = (
                str(facts.yield_strength_mpa)
                if facts.yield_strength_mpa is not None else None
            )
            fields.append("mechanical_properties.yield_strength_mpa")
        elif fraction == "72103002":
            inputs.update({
                "coating_metal": facts.coating_metal,
                "coating_process": facts.coating_process,
                "coating_both_sides": facts.coating_both_sides,
            })
            fields.extend((
                "coating.metal",
                "coating.process",
                "coating.superior_g_m2",
                "coating.inferior_g_m2",
            ))
        elif fraction in {"72083601", "72083701"}:
            inputs["yield_strength_mpa"] = (
                str(facts.yield_strength_mpa)
                if facts.yield_strength_mpa is not None else None
            )
            inputs["pipeline_steel"] = facts.pipeline_steel
            fields.extend(("mechanical_properties.yield_strength_mpa", "pipeline_steel"))
        return inputs, tuple(fields)

    def _steel_family(
        self, facts: ProductFacts
    ) -> tuple[str | None, set[str], tuple[str, ...], list[Decision]]:
        composition = facts.composition_pct
        steps: list[Decision] = []
        missing: set[str] = set()
        carbon = composition.get("C")
        chromium = composition.get("Cr")
        if carbon is None:
            missing.add("composition_pct.C")
        if chromium is None:
            missing.add("composition_pct.Cr")
        if carbon is not None and carbon > Decimal("2"):
            steps.append(Decision(
                "chapter72.definition.steel",
                StepOutcome.AMBIGUOUS,
                "El carbono supera 2%; se requiere validar la excepción aplicable a ciertos aceros al cromo.",
                {"C": str(carbon), "Cr": str(chromium) if chromium is not None else None},
                evidence_fields=("composition_pct.C", "composition_pct.Cr"),
            ))
            return None, {"steel_definition_exception"}, (
                "pig_iron", "ferroalloy", "chromium_steel_exception"
            ), steps
        stainless_known = carbon is not None and chromium is not None
        if stainless_known and carbon <= Decimal("1.2") and chromium >= Decimal("10.5"):
            steps.append(Decision(
                "chapter72.definition.stainless",
                StepOutcome.MATCHED,
                "Cumple C <= 1.2% y Cr >= 10.5%.",
                {"C": str(carbon), "Cr": str(chromium)},
                evidence_fields=("composition_pct.C", "composition_pct.Cr"),
            ))
            return "stainless", set(), (), steps
        if stainless_known:
            steps.append(Decision(
                "chapter72.definition.stainless",
                StepOutcome.NOT_MATCHED,
                "No cumple simultáneamente C <= 1.2% y Cr >= 10.5%.",
                {"C": str(carbon), "Cr": str(chromium)},
                evidence_fields=("composition_pct.C", "composition_pct.Cr"),
            ))

        matched_alloys: list[str] = []
        unknown_alloys: list[str] = []
        for element, threshold in ALLOY_THRESHOLDS.items():
            value = composition.get(element)
            if value is None:
                # Al_soluble above the threshold proves aluminium alloying, but
                # a lower soluble value cannot prove total aluminium is lower.
                if element == "Al_total" and composition.get("Al_soluble") is not None:
                    soluble = composition["Al_soluble"]
                    if soluble is not None and soluble >= threshold:
                        matched_alloys.append("Al_soluble")
                        continue
                unknown_alloys.append(element)
            elif value >= threshold:
                matched_alloys.append(element)
        if matched_alloys and stainless_known:
            steps.append(Decision(
                "chapter72.definition.other_alloy",
                StepOutcome.MATCHED,
                "Al menos un elemento alcanza el umbral de los demás aceros aleados.",
                {"matched_elements": matched_alloys},
                evidence_fields=tuple(
                    f"composition_pct.{element}" for element in matched_alloys
                ),
            ))
            return "other_alloy", set(), (), steps
        if matched_alloys and not stainless_known:
            steps.append(Decision(
                "chapter72.definition.steel_family",
                StepOutcome.AMBIGUOUS,
                "Hay un umbral de aleación, pero falta descartar acero inoxidable.",
                {"matched_elements": matched_alloys, "missing": sorted(missing)},
                evidence_fields=tuple(
                    f"composition_pct.{element}" for element in matched_alloys
                ),
            ))
            return None, missing, ("stainless", "other_alloy"), steps
        if unknown_alloys:
            missing.update(f"composition_pct.{element}" for element in unknown_alloys)
            steps.append(Decision(
                "chapter72.definition.non_alloy",
                StepOutcome.MISSING,
                "No se puede demostrar acero sin alear porque faltan elementos con umbrales legales.",
                {"missing_elements": unknown_alloys},
            ))
            candidates = ("non_alloy", "other_alloy")
            if not stainless_known:
                candidates = ("non_alloy", "stainless", "other_alloy")
            return None, missing, candidates, steps
        steps.append(Decision(
            "chapter72.definition.non_alloy",
            StepOutcome.MATCHED,
            "Todos los elementos requeridos están informados y debajo de los umbrales de aleación.",
        ))
        return "non_alloy", set(), (), steps

    def _heading_candidates(
        self, facts: ProductFacts, families: Iterable[str]
    ) -> tuple[str, ...]:
        return tuple(
            dict.fromkeys(
                heading
                for family in families
                for coated in ((False, True) if facts.coated is None else (facts.coated,))
                if (heading := self._heading(replace(facts, coated=coated), family)) is not None
            )
        )

    def _heading(self, facts: ProductFacts, family: str) -> str | None:
        assert facts.width_mm is not None
        if facts.coated is None:
            return None
        coated = facts.coated
        wide = facts.width_mm >= Decimal("600")
        if family == "non_alloy":
            if coated:
                return "7210" if wide else "7212"
            if facts.rolling == "hot":
                return "7208" if wide else "7211"
            if facts.rolling == "cold":
                return "7209" if wide else "7211"
        if family == "stainless":
            return "7219" if wide else "7220"
        if family == "other_alloy":
            return "7225" if wide else "7226"
        return None

    def _flat_rolled_branch(
        self, facts: ProductFacts, family: str
    ) -> tuple[str | None, str | None, set[str], tuple[str, ...], list[Decision]]:
        heading = self._heading(facts, family)
        steps = [Decision(
            "chapter72.flat_rolled.heading",
            StepOutcome.MATCHED if heading else StepOutcome.AMBIGUOUS,
            f"Partida candidata {heading}." if heading else "No existe una rama implementada para estas propiedades.",
            {"family": family, "width_mm": str(facts.width_mm), "rolling": facts.rolling,
             "coated": facts.coated, "coiled": facts.coiled},
            evidence_fields=("width_mm", "rolling", "coated", "coiled"),
        )]
        if heading == "7209":
            return (*self._non_alloy_cold_wide(facts), steps)
        if heading == "7210":
            fraction, nico, missing, candidates = self._non_alloy_coated_wide(facts)
            return fraction, nico, missing, candidates, steps
        if heading == "7208":
            fraction, nico, missing, candidates = self._non_alloy_hot_wide(facts)
            return fraction, nico, missing, candidates, steps
        if heading == "7225" and facts.rolling == "cold" and facts.coated is False:
            return "72255091", None, {"nico_qualifier"}, ("72255091" ,), steps
        return None, None, {"implemented_tariff_branch"}, ((heading,) if heading else ()), steps

    def _non_alloy_cold_wide(
        self, facts: ProductFacts
    ) -> tuple[str, str | None, set[str], tuple[str, ...]]:
        assert facts.thickness_mm is not None and facts.coiled is not None
        thickness = facts.thickness_mm
        if facts.coiled:
            if thickness >= Decimal("3"):
                fraction = "72091504"
                carbon = facts.composition_pct.get("C")
                if carbon is not None and carbon > Decimal("0.4"):
                    return fraction, "01", set(), ()
                if facts.yield_strength_mpa is not None and facts.yield_strength_mpa >= Decimal("355"):
                    return fraction, "02", set(), ()
                if facts.porcelain_exposed_parts is False and carbon is not None and facts.yield_strength_mpa is not None:
                    return fraction, "99", set(), ()
                return fraction, None, {"porcelain_exposed_parts"}, ("01", "02", "03", "99")
            if thickness > Decimal("1"):
                return self._high_strength_nico("72091601", facts)
            if thickness >= Decimal("0.5"):
                return self._high_strength_nico("72091701", facts)
            return "72091801", ("01" if thickness < Decimal("0.361") else "99"), set(), ()
        if thickness >= Decimal("3"):
            return "72092501", "00", set(), ()
        if thickness > Decimal("1"):
            return "72092601", "00", set(), ()
        if thickness >= Decimal("0.5"):
            return "72092701", "00", set(), ()
        return "72092801", "00", set(), ()

    @staticmethod
    def _high_strength_nico(
        fraction: str, facts: ProductFacts
    ) -> tuple[str, str | None, set[str], tuple[str, ...]]:
        if facts.yield_strength_mpa is None:
            return fraction, None, {"yield_strength_mpa"}, ("01", "99")
        nico = "01" if facts.yield_strength_mpa >= Decimal("355") else "99"
        return fraction, nico, set(), ()

    @staticmethod
    def _non_alloy_coated_wide(
        facts: ProductFacts,
    ) -> tuple[str | None, str | None, set[str], tuple[str, ...]]:
        metal = (facts.coating_metal or "").casefold()
        process = (facts.coating_process or "").casefold()
        if metal in {"zn", "zinc", "zincado", "cinc"} and process in {
            "electrolytic", "electrolytic zinc", "electrogalvanized",
        }:
            if facts.coating_both_sides is None:
                return "72103002", None, {"coating_both_sides"}, ("01", "99")
            return "72103002", ("01" if facts.coating_both_sides else "99"), set(), ()
        return None, None, {"coating_type"}, ("7210",)

    @staticmethod
    def _non_alloy_hot_wide(
        facts: ProductFacts,
    ) -> tuple[str | None, str | None, set[str], tuple[str, ...]]:
        assert facts.thickness_mm is not None and facts.coiled is not None
        if facts.pattern_in_relief is True:
            if facts.coiled:
                nico = "01" if facts.thickness_mm > 10 else "02" if facts.thickness_mm > Decimal("4.75") else None
                if nico is None:
                    if facts.thickness_mm == Decimal("4.75"):
                        return "72081003", None, {"source_boundary_4_75_mm"}, ("02", "03", "99")
                    if facts.pickled is False:
                        return "72081003", "03", set(), ()
                    if facts.pickled is True:
                        return "72081003", "99", set(), ()
                    return "72081003", None, {"pickled"}, ("03", "99")
                return "72081003", nico, set(), ()
            nico = "01" if facts.thickness_mm > Decimal("4.75") else "99"
            return "72084002", nico, set(), ()
        if facts.pattern_in_relief is None:
            if facts.coiled:
                pickled_fraction, unpickled_fraction = (
                    Chapter72ClassificationEngine._hot_coiled_fractions(facts.thickness_mm)
                )
                return None, None, {"pattern_in_relief"}, (
                    "72081003", pickled_fraction, unpickled_fraction
                )
            flat_fraction = (
                "72085104" if facts.thickness_mm > Decimal("10")
                else "72085201" if facts.thickness_mm >= Decimal("4.75")
                else "72085301" if facts.thickness_mm >= Decimal("3")
                else "72085401"
            )
            return None, None, {"pattern_in_relief"}, ("72084002", flat_fraction)
        if not facts.coiled:
            fraction = (
                "72085104" if facts.thickness_mm > Decimal("10")
                else "72085201" if facts.thickness_mm >= Decimal("4.75")
                else "72085301" if facts.thickness_mm >= Decimal("3")
                else "72085401"
            )
            if fraction == "72085104":
                return fraction, None, {"nico_qualifier"}, ("01", "02", "03", "04", "05")
            return fraction, "00", set(), ()
        if facts.pickled is None:
            return None, None, {"pickled"}, (
                *Chapter72ClassificationEngine._hot_coiled_fractions(facts.thickness_mm),
            )
        if facts.pickled:
            fraction = "72082502" if facts.thickness_mm >= Decimal("4.75") else "72082601" if facts.thickness_mm >= Decimal("3") else "72082701"
        else:
            fraction = "72083601" if facts.thickness_mm > Decimal("10") else "72083701" if facts.thickness_mm >= Decimal("4.75") else "72083801" if facts.thickness_mm >= Decimal("3") else "72083901"
        if fraction == "72082502":
            return fraction, ("01" if facts.thickness_mm > Decimal("10") else "99"), set(), ()
        if fraction in {"72083601", "72083701"}:
            if facts.yield_strength_mpa is not None and facts.yield_strength_mpa >= Decimal("355"):
                return fraction, "01", set(), ()
            if facts.pipeline_steel is True:
                return fraction, "02", set(), ()
            if facts.yield_strength_mpa is not None and facts.pipeline_steel is False:
                return fraction, "99", set(), ()
            return fraction, None, {"yield_strength_mpa", "pipeline_steel"}, ("01", "02", "99")
        return Chapter72ClassificationEngine._high_strength_nico(fraction, facts)

    @staticmethod
    def _hot_coiled_fractions(thickness: Decimal) -> tuple[str, str]:
        pickled = (
            "72082502" if thickness >= Decimal("4.75")
            else "72082601" if thickness >= Decimal("3")
            else "72082701"
        )
        unpickled = (
            "72083601" if thickness > Decimal("10")
            else "72083701" if thickness >= Decimal("4.75")
            else "72083801" if thickness >= Decimal("3")
            else "72083901"
        )
        return pickled, unpickled

    def _result(
        self,
        outcome: ClassificationOutcome,
        product_type: str | None,
        fraction: str | None,
        nico: str | None,
        missing: set[str],
        candidates: Iterable[str],
        steps: list[Decision],
        facts: ProductFacts,
    ) -> ClassificationDecision:
        description = self.catalog.description(fraction, nico) if fraction else None
        raw_candidates = tuple(candidates)
        ranked_candidates = self._ranked_candidates(
            fraction=fraction,
            nico=nico,
            raw_candidates=raw_candidates,
            missing=missing,
            facts=facts,
        )
        if outcome is ClassificationOutcome.CLASSIFIED and len(ranked_candidates) != 3:
            outcome = ClassificationOutcome.NEEDS_REVIEW
            missing.add("three_valid_candidates")
            steps.append(Decision(
                "chapter72.candidates.exactly_three",
                StepOutcome.MISSING,
                "La revisión requiere exactamente tres opciones válidas de fracción y NICO.",
                {"valid_candidate_count": len(ranked_candidates)},
            ))
        return ClassificationDecision(
            outcome=outcome,
            product_type=product_type,
            fraction=fraction,
            nico=nico,
            description=description,
            missing_fields=tuple(sorted(missing)),
            candidates=raw_candidates,
            ranked_candidates=ranked_candidates,
            steps=tuple(steps),
        )

    def _ranked_candidates(
        self,
        *,
        fraction: str | None,
        nico: str | None,
        raw_candidates: tuple[str, ...],
        missing: set[str],
        facts: ProductFacts,
    ) -> tuple[ClassificationCandidate, ...]:
        pairs: list[tuple[int, str, str, str]] = []
        if fraction is not None and nico is not None:
            pairs.append((-100, fraction, nico, "fully_supported" if not missing else "conditional"))
        for raw_index, raw in enumerate(raw_candidates):
            compact = raw.replace(".", "").replace("-", "")
            if fraction is not None and len(compact) == 2 and compact.isdigit():
                pairs.append((raw_index, fraction, compact, "conditional"))
            elif len(compact) == 8 and compact.isdigit():
                for entry in self.catalog.nicos_for_fraction(compact):
                    candidate_nico = str(entry.raw.get("nico") or entry.code[-2:])
                    compatible, qualifier_priority = self._candidate_compatibility(
                        facts, compact, candidate_nico
                    )
                    if compatible:
                        pairs.append((
                            raw_index * 100 + qualifier_priority,
                            compact,
                            candidate_nico,
                            "conditional",
                        ))
            elif len(compact) == 10 and compact.isdigit():
                pairs.append((raw_index, compact[:8], compact[8:], "conditional"))

        unique: list[tuple[int, str, str, str]] = []
        seen: set[tuple[str, str]] = set()
        for priority, candidate_fraction, candidate_nico, support_level in sorted(
            pairs, key=lambda item: item[0]
        ):
            key = (candidate_fraction, candidate_nico)
            if key in seen:
                continue
            try:
                self.catalog.validate_result(candidate_fraction, candidate_nico)
            except ValueError:
                continue
            seen.add(key)
            unique.append((priority, candidate_fraction, candidate_nico, support_level))

        return tuple(
            ClassificationCandidate(
                rank=rank,
                fraction=candidate_fraction,
                nico=candidate_nico,
                description=self.catalog.description(candidate_fraction, candidate_nico),
                support_level=support_level,
                missing_fields=tuple(sorted(missing)) if support_level == "conditional" else (),
            )
            for rank, (_, candidate_fraction, candidate_nico, support_level) in enumerate(
                unique[:3], start=1
            )
        )

    @staticmethod
    def _candidate_compatibility(
        facts: ProductFacts,
        fraction: str,
        nico: str,
    ) -> tuple[bool, int]:
        thickness = facts.thickness_mm
        if fraction == "72081003" and thickness is not None:
            valid = {
                "01": thickness > Decimal("10"),
                "02": Decimal("4.75") < thickness <= Decimal("10"),
                "03": thickness < Decimal("4.75"),
                "99": thickness <= Decimal("4.75"),
            }.get(nico, True)
            return valid, 10 if nico == "99" else 0
        if fraction == "72082502" and thickness is not None:
            valid = thickness > Decimal("10") if nico == "01" else thickness <= Decimal("10")
            return valid, 10 if nico == "99" else 0
        if fraction in {"72083601", "72083701"}:
            if nico == "01" and facts.yield_strength_mpa is not None:
                return facts.yield_strength_mpa >= Decimal("355"), 0
            if nico == "02" and facts.pipeline_steel is not None:
                return facts.pipeline_steel, 0
            return True, 10 if nico == "99" else 0
        if fraction == "72255091":
            boron = facts.composition_pct.get("B")
            boron_grade = nico in {"01", "02", "03", "04", "05", "06", "07"}
            if boron_grade and boron is not None and boron < Decimal("0.0008"):
                return False, 0
            if boron_grade and thickness is not None:
                dimensions = {
                    "01": facts.coiled is not False and Decimal("1") < thickness < Decimal("3"),
                    "02": facts.coiled is not False and Decimal("0.5") <= thickness <= Decimal("1"),
                    "03": facts.coiled is not False and thickness < Decimal("0.5"),
                    "04": facts.coiled is not False and Decimal("3") <= thickness < Decimal("4.75"),
                    "05": facts.coiled is not False and thickness >= Decimal("4.75"),
                    "06": facts.coiled is not True and thickness < Decimal("4.75"),
                    "07": facts.coiled is not True and thickness >= Decimal("4.75"),
                }
                if not dimensions[nico]:
                    return False, 0
            if boron_grade:
                return True, 0
            if nico == "10":
                return (
                    thickness is None or thickness >= Decimal("4.75")
                ) and facts.porcelain_exposed_parts is not False, 20
            if nico == "11" and facts.yield_strength_mpa is not None:
                return facts.yield_strength_mpa >= Decimal("355"), 0
            if nico == "91" and thickness is not None:
                return thickness >= Decimal("4.75"), 10
            if nico == "92" and facts.porcelain_exposed_parts is False:
                return False, 20
            return True, 10 if nico == "99" else 20
        return True, 10 if nico == "99" else 0
