from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from typing import Iterable

from backend.app.classification_engine.catalog import SourceProvidedCatalog
from backend.app.classification_engine.models import (
    CandidateFactor,
    ClassificationCandidate,
    ClassificationDecision,
    ClassificationOutcome,
    Decision,
    DiscardedCandidate,
    ProductFacts,
    StepOutcome,
)
from backend.app.classification_engine.nico_rules import (
    assessed_nico, conditions_for, observation,
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
        self.source_sha256 = sha256(
            Path(__file__).read_bytes() + Path(__file__).with_name("nico_rules.py").read_bytes()
        ).hexdigest()

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

        if facts.coiled is False and (
            (facts.thickness_mm < Decimal("4.75") and facts.width_mm < 10 * facts.thickness_mm)
            or (facts.thickness_mm >= Decimal("4.75") and (
                facts.width_mm <= Decimal("150") or facts.thickness_mm > facts.width_mm / 2
            ))
        ):
            steps.append(Decision(
                "chapter72.flat_rolled.definition", StepOutcome.CONFLICT,
                "Las dimensiones sin enrollar contradicen la definición de producto laminado plano de la Nota 1(k).",
                evidence_fields=("width_mm", "thickness_mm", "coiled"),
            ))
            return self._result(ClassificationOutcome.NEEDS_REVIEW, "flat_rolled", None, None,
                                {"flat_rolled_definition"}, (), steps, facts)

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
        if fraction is not None and nico is not None:
            assessment = assessed_nico(facts, fraction, nico)
            if assessment in {StepOutcome.UNKNOWN, StepOutcome.CONFLICT}:
                missing.add("nico_qualifier")
                candidates = (fraction,)
                nico = None
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
        matched_alloys.extend(
            element for element, value in composition.items()
            if element not in {*ALLOY_THRESHOLDS, "C", "N", "P", "S", "Fe", "Al_soluble"}
            and value is not None and value >= Decimal("0.1")
        )
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
        if carbon is None:
            return None, missing, ("non_alloy",), steps
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
        if heading == "7208":
            fraction, nico, missing, candidates = self._non_alloy_hot_wide(facts)
            return fraction, nico, missing, candidates, steps
        if heading == "7209":
            return (*self._non_alloy_cold_wide(facts), steps)
        if heading == "7210":
            fraction, nico, missing, candidates = self._non_alloy_coated_wide(facts)
            return fraction, nico, missing, candidates, steps
        if heading == "7211":
            fraction, nico, missing, candidates = self._non_alloy_narrow(facts)
            return fraction, nico, missing, candidates, steps
        if heading == "7212":
            fraction, nico, missing, candidates = self._non_alloy_coated_narrow(facts)
            return fraction, nico, missing, candidates, steps
        if heading == "7219":
            fraction, nico, missing, candidates = self._stainless_wide(facts)
            if "ambiguous_source_code_7219_35_02" in missing:
                steps.append(Decision(
                    "chapter72.stainless.source_anomaly_7219_35_02",
                    StepOutcome.AMBIGUOUS,
                    "Anomalía en la fuente original (PDF LIGIE SIN VIGENCIA páginas 38-39): la fracción 7219.35.02 aparece duplicada con distintas descripciones.",
                    {"fraction": fraction, "thickness_mm": str(facts.thickness_mm)},
                    evidence_fields=("thickness_mm",),
                ))
            return fraction, nico, missing, candidates, steps
        if heading == "7220":
            fraction, nico, missing, candidates = self._stainless_narrow(facts)
            return fraction, nico, missing, candidates, steps
        if heading == "7225":
            fraction, nico, missing, candidates = self._other_alloy_wide(facts)
            return fraction, nico, missing, candidates, steps
        if heading == "7226":
            fraction, nico, missing, candidates = self._other_alloy_narrow(facts)
            return fraction, nico, missing, candidates, steps
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
                missing = {"porcelain_exposed_parts"}
                if facts.deep_drawing_class is None:
                    missing.add("deep_drawing_class")
                return fraction, None, missing, ("01", "02", "03", "99")
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

        # Tinplate / estañados (7210.11 / 7210.12)
        if metal in {"sn", "tin", "estaño", "estano", "hojalata"}:
            if facts.thickness_mm is not None and facts.thickness_mm >= Decimal("0.5"):
                return "72101101", "00", set(), ()
            if facts.secondary_reduction_ratio is None or facts.can_body_end_use is None:
                return "72101204", None, {
                    "secondary_reduction_ratio", "can_body_end_use"
                }, ("01", "02", "99")
            return "72101204", None, {"official_nico_qualifier"}, ("01", "02", "03", "99")

        # Lead / terne (7210.20)
        if metal in {"pb", "lead", "plomo", "terne"}:
            return "72102001", "00", set(), ()

        # Electrolytic zinc (7210.30)
        if metal in {"zn", "zinc", "zincado", "cinc"} and process in {
            "electrolytic", "electrolytic zinc", "electrogalvanized",
        }:
            if facts.coating_both_sides is None:
                return "72103002", None, {"coating_both_sides"}, ("01", "99")
            return "72103002", ("01" if facts.coating_both_sides else "99"), set(), ()

        # Hot-dip galvanized / otros cincados (7210.41 / 7210.49)
        if metal in {"zn", "zinc", "zincado", "cinc", "galvanizado", "galvanized"}:
            if not process:
                return None, None, {"coating_process"}, ("72103002", "72104999")
            if facts.pattern_in_relief is True:
                if facts.coating_both_sides is None:
                    return None, None, {"coating_both_sides"}, ("72104101", "72104199")
                return ("72104101" if facts.coating_both_sides else "72104199"), "00", set(), ()
            if facts.pattern_in_relief is None:
                return None, None, {"pattern_in_relief"}, ("72104101", "72104199", "72104999")
            fraction = "72104999"
            if facts.yield_strength_mpa is not None and facts.yield_strength_mpa >= Decimal("355"):
                return fraction, "02", set(), ()
            if facts.yield_strength_mpa is None:
                return fraction, None, {"yield_strength_mpa"}, (fraction,)
            if facts.thickness_mm < Decimal("3") and facts.yield_strength_mpa >= Decimal("275"):
                return fraction, "01", set(), ()
            return fraction, "99", set(), ()

        # Chromium oxides / TFS (7210.50)
        if metal in {"cr_oxide", "cr", "cromo", "tfs", "oxido de cromo"}:
            return "72105003", None, {"temper", "nico_qualifier"}, ("72105003",)

        # Aluminum-zinc alloy (7210.61)
        if metal in {"al-zn", "aluzinc", "galvalume", "aluminio-cinc", "aluminio cinc"}:
            return "72106101", "00", set(), ()

        # Aluminum other (7210.69)
        if metal in {"al", "aluminio", "aluminum"}:
            return "72106999", None, {"coating_alloy_composition"}, ("72106999",)

        # Painted / plastic (7210.70)
        if metal in {"paint", "plastic", "pintado", "plastico", "barniz", "prepintado"}:
            return "72107002", None, {"coating_layer_details"}, ("72107002",)

        if metal:
            return "72109099", None, {"cladding_material"}, ("72109099",)

        return None, None, {"coating_metal"}, (
            "72101101", "72103002", "72104999", "72106101", "72107002"
        )

    @staticmethod
    def _non_alloy_narrow(
        facts: ProductFacts,
    ) -> tuple[str | None, str | None, set[str], tuple[str, ...]]:
        thickness = facts.thickness_mm
        carbon = facts.composition_pct.get("C")

        if facts.rolling == "hot":
            if facts.rolled_four_faces is True:
                if facts.width_mm > Decimal("150") and thickness >= Decimal("4") and facts.coiled is False and facts.pattern_in_relief is False:
                    return "72111301", "00", set(), ()
                if facts.pattern_in_relief is None and facts.width_mm > Decimal("150") and thickness >= Decimal("4") and facts.coiled is False:
                    return None, None, {"pattern_in_relief"}, ("72111301",)
            if thickness is not None:
                fraction = "72111491" if thickness >= Decimal("4.75") else "72111999"
                if fraction == "72111491" and facts.coiled is True:
                    return fraction, "03", set(), ()
                return fraction, None, {"product_kind", "nico_qualifier"}, (fraction,)

        if facts.rolling == "cold":
            if carbon is not None and carbon >= Decimal("0.25"):
                fraction = "72112999"
                return fraction, None, {"product_kind", "nico_qualifier"}, (fraction,)
            fraction = "72112303"
            return fraction, None, {"product_kind", "nico_qualifier"}, (fraction,)

        return "72119099", "00", set(), ()

    @staticmethod
    def _non_alloy_coated_narrow(
        facts: ProductFacts,
    ) -> tuple[str | None, str | None, set[str], tuple[str, ...]]:
        metal = (facts.coating_metal or "").casefold()
        process = (facts.coating_process or "").casefold()

        if facts.clad is True:
            if facts.cladding_weight_percentage is None:
                return "72126004", None, {"cladding_weight_percentage"}, ("72126004",)
            return "72126004", None, {"cladding_material"}, ("72126004",)
        if metal in {"sn", "tin", "estaño", "estano", "hojalata"}:
            return "72121003", None, {"product_kind"}, ("72121003",)
        if metal in {"zn", "zinc", "cinc"} and process in {"electrolytic", "electrogalvanized"}:
            return "72122003", None, {"product_kind", "coating_both_sides"}, ("72122003",)
        if metal in {"zn", "zinc", "cinc", "galvanizado"}:
            return "72123003", None, {"product_kind", "coating_both_sides", "coating_process"}, ("72123003",)
        if metal in {"paint", "plastic", "pintado", "plastico"}:
            return "72124004", None, {"coating_layer_details"}, ("72124004",)
        if not metal:
            return None, None, {"coating_metal"}, ()
        return "72125001", "00", set(), ()

    @staticmethod
    def _stainless_wide(
        facts: ProductFacts,
    ) -> tuple[str | None, str | None, set[str], tuple[str, ...]]:
        thickness = facts.thickness_mm
        if thickness is None:
            return None, None, {"thickness_mm"}, ("72191301", "72193301")

        series = facts.stainless_series
        nico = {"200": "01", "300": "02", "400": "03"}.get(series)
        series_missing = {"stainless_series"} if series is None else set()
        if series is not None and nico is None:
            nico = "99"

        if facts.rolling == "hot":
            if facts.coiled is True:
                fraction = (
                    "72191101" if thickness > Decimal("10")
                    else "72191202" if thickness >= Decimal("4.75")
                    else "72191301" if thickness >= Decimal("3")
                    else "72191401"
                )
                if fraction == "72191101":
                    return fraction, "00", set(), ()
                if fraction == "72191202":
                    dimensional_nico = "01" if thickness <= Decimal("6") and Decimal("710") <= facts.width_mm <= Decimal("1350") else "99"
                    return fraction, dimensional_nico, set(), ()
                return fraction, nico, series_missing, (fraction,) if nico is None else ()
            if facts.coiled is False:
                fraction = (
                    "72192101" if thickness > Decimal("10")
                    else "72192201" if thickness >= Decimal("4.75")
                    else "72192301" if thickness >= Decimal("3")
                    else "72192401"
                )
                if fraction in {"72192101", "72192301", "72192401"}:
                    return fraction, "00", set(), ()
                return fraction, nico, series_missing, (fraction,) if nico is None else ()
            return None, None, {"coiled"}, ("72191301", "72192301")

        if facts.rolling == "cold":
            if thickness >= Decimal("4.75"):
                return "72193101", ("01" if facts.coiled else "99"), set(), ()
            if thickness >= Decimal("3"):
                if series in {"200", "300", "400"}:
                    nico = ({"200": "02", "300": "03", "400": "04"} if thickness <= Decimal("4") else {"200": "91", "300": "92", "400": "93"})[series]
                return "72193202", nico, series_missing, ("72193202",) if nico is None else ()
            if thickness > Decimal("1"):
                return "72193301", nico, series_missing, ("72193301",) if nico is None else ()

            # Source anomaly detection for 7219.35.02:
            # Documented in data/ligie/chapter-72/source-provided/SOURCE.md
            # Page 38 (under 7219.34) and Page 39 (under 7219.35) both list 7219.35.02 with conflicting entries.
            return (
                "72193502",
                None,
                {"ambiguous_source_code_7219_35_02"},
                ("72193502",),
            )

        return "72199099", "00", set(), ()

    @staticmethod
    def _stainless_narrow(
        facts: ProductFacts,
    ) -> tuple[str | None, str | None, set[str], tuple[str, ...]]:
        thickness = facts.thickness_mm
        if facts.rolling == "hot":
            if thickness is not None and thickness >= Decimal("4.75"):
                return "72201101", "00", set(), ()
            return "72201201", "00", set(), ()
        if facts.rolling == "cold":
            return "72202003", None, {"stainless_series", "temper", "nico_qualifier"}, ("72202003",)
        return "72209099", "00", set(), ()

    def _other_alloy_wide(
        self, facts: ProductFacts
    ) -> tuple[str | None, str | None, set[str], tuple[str, ...]]:
        # Silicon electrical steel (7225.11 / 7225.19)
        if facts.magnetic_silicon is True or facts.grain_oriented is True:
            missing = {
                name for name, value in (
                    ("magnetic_loss_w_per_kg", facts.magnetic_loss_w_per_kg),
                    ("magnetic_induction_tesla", facts.magnetic_induction_tesla),
                ) if value is None
            }
            if facts.grain_oriented is True:
                return "72251101", (None if missing else "00"), missing, ("72251101",)
            return "72251999", (None if missing else "00"), missing, ("72251999",)

        # Coated other alloy (7225.91 / 7225.92 / 7225.99)
        if facts.coated is True:
            metal = (facts.coating_metal or "").casefold()
            process = (facts.coating_process or "").casefold()
            if metal in {"zn", "zinc", "cinc"} and process in {"electrolytic", "electrogalvanized"}:
                return "72259101", "00", set(), ()
            if metal in {"zn", "zinc", "cinc", "galvanizado"}:
                if not process:
                    return None, None, {"coating_process"}, ("72259101", "72259201")
                return self._high_strength_nico("72259201", facts)
            return "72259999", None, {"coating_layer_details"}, ("72259999",)

        # Hot-rolled other alloy (7225.30 / 7225.40)
        if facts.rolling == "hot":
            if facts.coiled is True:
                return "72253091", None, {"nico_qualifier"}, ("72253091",)
            if facts.coiled is False:
                return "72254091", None, {"nico_qualifier"}, ("72254091",)
            return None, None, {"coiled"}, ("72253091", "72254091")

        # Cold-rolled other alloy (7225.50)
        if facts.rolling == "cold" and facts.coated is False:
            missing = {"nico_qualifier"}
            if facts.deep_drawing_class is None:
                missing.add("deep_drawing_class")
            return "72255091", None, missing, ("72255091",)

        return None, None, {"implemented_tariff_branch"}, ("7225",)

    @staticmethod
    def _other_alloy_narrow(
        facts: ProductFacts,
    ) -> tuple[str | None, str | None, set[str], tuple[str, ...]]:
        if facts.grain_oriented is True:
            missing = Chapter72ClassificationEngine._magnetic_missing(facts)
            return "72261101", (None if missing else "00"), missing, ("72261101",)
        if facts.magnetic_silicon is True:
            missing = Chapter72ClassificationEngine._magnetic_missing(facts)
            return "72261999", (None if missing else "00"), missing, ("72261999",)
        if facts.high_speed_steel is True:
            return "72262001", "00", set(), ()
        if facts.coated is True:
            return "72269999", None, {"nico_qualifier", "coating_process"}, ("72269999",)
        if facts.rolling == "hot":
            return "72269107", None, {"nico_qualifier"}, ("72269107",)
        if facts.rolling == "cold":
            return "72269206", None, {"nico_qualifier"}, ("72269206",)
        return "72269999", None, {"nico_qualifier"}, ("72269999",)

    @staticmethod
    def _magnetic_missing(facts: ProductFacts) -> set[str]:
        return {
            name for name, value in (
                ("magnetic_loss_w_per_kg", facts.magnetic_loss_w_per_kg),
                ("magnetic_induction_tesla", facts.magnetic_induction_tesla),
            ) if value is None
        }

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
        ranked_candidates, discarded_candidates = self._ranked_candidates(
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
            discarded_candidates=discarded_candidates,
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
    ) -> tuple[tuple[ClassificationCandidate, ...], tuple[DiscardedCandidate, ...]]:
        pairs: list[tuple[int, str, str, str]] = []
        discarded: list[DiscardedCandidate] = []
        if fraction is not None and nico is not None:
            pairs.append((-100, fraction, nico, "fully_supported" if not missing else "conditional"))
        for raw_index, raw in enumerate(raw_candidates):
            compact = raw.replace(".", "").replace("-", "")
            if fraction is not None and len(compact) == 2 and compact.isdigit():
                compatible, qualifier_priority = self._candidate_compatibility(
                    facts, fraction, compact
                )
                if compatible:
                    pairs.append((
                        raw_index + qualifier_priority,
                        fraction,
                        compact,
                        "conditional",
                    ))
                else:
                    discarded.append(DiscardedCandidate(
                        fraction=fraction,
                        nico=compact,
                        reason_code="known_facts_conflict",
                        explanation="La opción contradice propiedades conocidas del producto.",
                    ))
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
                    else:
                        discarded.append(DiscardedCandidate(
                            fraction=compact,
                            nico=candidate_nico,
                            reason_code="known_facts_conflict",
                            explanation="La opción contradice propiedades conocidas del producto.",
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
            compatible, _ = self._candidate_compatibility(facts, candidate_fraction, candidate_nico)
            if not compatible:
                discarded.append(DiscardedCandidate(
                    fraction=candidate_fraction, nico=candidate_nico,
                    reason_code="known_facts_conflict",
                    explanation="La opción contradice propiedades conocidas del producto.",
                ))
                continue
            try:
                self.catalog.validate_result(candidate_fraction, candidate_nico)
            except ValueError:
                discarded.append(DiscardedCandidate(
                    fraction=candidate_fraction,
                    nico=candidate_nico,
                    reason_code="source_catalog_invalid",
                    explanation="La combinación no es única o no existe en el catálogo versionado.",
                ))
                continue
            seen.add(key)
            unique.append((priority, candidate_fraction, candidate_nico, support_level))

        ranked_list: list[ClassificationCandidate] = []
        for rank, (_, candidate_fraction, candidate_nico, support_level) in enumerate(
            unique[:3], start=1
        ):
            factors = self._candidate_factors(
                facts, candidate_fraction, candidate_nico, support_level
            )
            candidate_missing = set(missing) if support_level == "conditional" else set()
            if support_level == "conditional":
                for factor in factors:
                    if factor.outcome is StepOutcome.UNKNOWN:
                        candidate_missing.add("nico_qualifier")
                        for field_name, value in factor.observed.items():
                            if value is None:
                                candidate_missing.add(field_name)
            ranked_list.append(
                ClassificationCandidate(
                    rank=rank,
                    fraction=candidate_fraction,
                    nico=candidate_nico,
                    description=self.catalog.description(candidate_fraction, candidate_nico),
                    support_level=support_level,
                    missing_fields=tuple(sorted(candidate_missing)),
                    factors=factors,
                )
            )
        ranked = tuple(ranked_list)
        discarded.extend(
            DiscardedCandidate(
                fraction=candidate_fraction,
                nico=candidate_nico,
                reason_code="outside_top_three",
                explanation="La opción es válida, pero quedó fuera de las tres mejor respaldadas.",
            )
            for _, candidate_fraction, candidate_nico, _ in unique[3:]
        )
        return ranked, tuple(discarded)

    @staticmethod
    def _candidate_compatibility(
        facts: ProductFacts,
        fraction: str,
        nico: str,
    ) -> tuple[bool, int]:
        thickness = facts.thickness_mm
        if fraction == "72104999" and facts.pattern_in_relief is True:
            return False, 0
        assessment = assessed_nico(facts, fraction, nico)
        if assessment is not None:
            boron = facts.composition_pct.get("B")
            partially_supported = fraction == "72255091" and nico in {"01", "02", "03", "04", "05", "06", "07"} and boron is not None and boron >= Decimal("0.0008")
            priority = 10 if nico == "99" else 20 if assessment is StepOutcome.UNKNOWN and not partially_supported else 0
            return assessment is not StepOutcome.CONFLICT, priority
        if fraction == "72091504":
            carbon = facts.composition_pct.get("C")
            if nico == "01" and carbon is not None:
                return carbon > Decimal("0.4"), 0
            if nico == "02" and facts.yield_strength_mpa is not None:
                return facts.yield_strength_mpa >= Decimal("355"), 0
            if nico == "03" and facts.porcelain_exposed_parts is not None:
                return facts.porcelain_exposed_parts, 0
            if nico == "99" and all(
                value is not None
                for value in (carbon, facts.yield_strength_mpa, facts.porcelain_exposed_parts)
            ):
                return (
                    carbon <= Decimal("0.4")
                    and facts.yield_strength_mpa < Decimal("355")
                    and facts.porcelain_exposed_parts is False
                ), 10
            return True, 10 if nico == "99" else 20
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
        return True, 10 if nico == "99" else 0

    def _candidate_factors(
        self,
        facts: ProductFacts,
        fraction: str,
        nico: str,
        support_level: str,
    ) -> tuple[CandidateFactor, ...]:
        factors: list[CandidateFactor] = []
        matched_alloys = {
            element: value
            for element, threshold in ALLOY_THRESHOLDS.items()
            if (value := facts.composition_pct.get(element)) is not None
            and value >= threshold
        }
        if "Al_total" not in matched_alloys and facts.composition_pct.get("Al_total") is None:
            soluble = facts.composition_pct.get("Al_soluble")
            if soluble is not None and soluble >= ALLOY_THRESHOLDS["Al_total"]:
                matched_alloys["Al_soluble"] = soluble
        matched_alloys.update({
            element: value for element, value in facts.composition_pct.items()
            if element not in {*ALLOY_THRESHOLDS, "C", "N", "P", "S", "Fe", "Al_soluble"}
            and value is not None and value >= Decimal("0.1")
        })
        if fraction.startswith(("7225", "7226")) and matched_alloys:
            factors.append(CandidateFactor(
                sequence=len(factors) + 1,
                rule_code="chapter72.definition.other_alloy",
                outcome=StepOutcome.MATCHED,
                explanation="Al menos un elemento alcanza el umbral de acero aleado.",
                operator=">=",
                expected={
                    element: str(ALLOY_THRESHOLDS.get(element, ALLOY_THRESHOLDS["Al_total"] if element == "Al_soluble" else Decimal("0.1")))
                    for element in matched_alloys
                },
                observed={element: str(value) for element, value in matched_alloys.items()},
                unit="%",
                evidence_fields=tuple(
                    f"composition_pct.{element}" for element in matched_alloys
                ),
            ))
        elif fraction.startswith(("7219", "7220")):
            cr = facts.composition_pct.get("Cr")
            c = facts.composition_pct.get("C")
            if cr is not None and cr >= Decimal("10.5"):
                factors.append(CandidateFactor(
                    sequence=len(factors) + 1,
                    rule_code="chapter72.definition.stainless_steel",
                    outcome=StepOutcome.MATCHED,
                    explanation="Contenido de cromo >= 10.5% y carbono <= 1.2% (acero inoxidable).",
                    operator=">=",
                    expected={"Cr": "10.5", "C": "1.2"},
                    observed={"Cr": str(cr), "C": str(c) if c is not None else None},
                    unit="%",
                    evidence_fields=("composition_pct.Cr", "composition_pct.C"),
                ))
        elif fraction.startswith(("7208", "7209", "7210", "7211", "7212")) and not matched_alloys:
            sample_elements = tuple(e for e in ("B", "Cr", "Ni", "Mo", "Ti") if e in facts.composition_pct)
            if sample_elements:
                factors.append(CandidateFactor(
                    sequence=len(factors) + 1,
                    rule_code="chapter72.definition.non_alloy",
                    outcome=StepOutcome.MATCHED,
                    explanation="Los elementos de aleación analizados se encuentran estrictamente por debajo de los umbrales de la Nota 1(f).",
                    operator="<",
                    expected={e: str(ALLOY_THRESHOLDS[e]) for e in sample_elements},
                    observed={e: str(facts.composition_pct[e]) for e in sample_elements},
                    unit="%",
                    evidence_fields=tuple(f"composition_pct.{e}" for e in sample_elements),
                ))

        factors.append(CandidateFactor(
            sequence=len(factors) + 1,
            rule_code=f"chapter72.fraction.{fraction}",
            outcome=StepOutcome.MATCHED,
            explanation=f"Las propiedades conocidas son compatibles con la fracción {fraction}.",
            operator="all",
            expected={"fraction": fraction},
            observed={
                "width_mm": str(facts.width_mm) if facts.width_mm is not None else None,
                "thickness_mm": str(facts.thickness_mm) if facts.thickness_mm is not None else None,
                "rolling": facts.rolling,
                "coiled": facts.coiled,
                "coated": facts.coated,
            },
            unit=None,
            evidence_fields=("width_mm", "thickness_mm", "rolling", "coiled", "coated"),
        ))

        catalog_description = self.catalog.description(fraction, nico)
        observed, evidence_fields = self._nico_observations(facts, fraction, nico)
        expected = self._nico_expectation(fraction, nico)
        conditions = conditions_for(fraction, nico)
        assessment = assessed_nico(facts, fraction, nico)
        if conditions is not None:
            expected = {"conditions": [
                {"field": condition.field, "operator": condition.operator, "value": condition.value}
                for condition in conditions
            ]}
            evidence_fields = tuple(dict.fromkeys(condition.field for condition in conditions))
            observed = {
                field: str(value) if isinstance(value := observation(facts, field), Decimal) else value
                for field in evidence_fields
            }
        expected["description"] = catalog_description
        # Compatibility alone does not prove a conditional legal qualifier.
        nico_outcome = assessment or (
            StepOutcome.MATCHED if support_level == "fully_supported" else StepOutcome.UNKNOWN
        )
        factors.append(CandidateFactor(
            sequence=len(factors) + 1,
            rule_code=f"chapter72.nico.{fraction}.{nico}",
            outcome=nico_outcome,
            explanation=(
                f"Cumple la condición del NICO {nico}."
                if nico_outcome is StepOutcome.MATCHED
                else f"El NICO {nico} es posible; el personal debe verificar su condición específica."
            ),
            operator="catalog_qualifier",
            expected=expected,
            observed=observed,
            evidence_fields=evidence_fields,
            required_for_selection=True,
        ))
        return tuple(factors)

    @staticmethod
    def _nico_expectation(fraction: str, nico: str) -> dict[str, object]:
        if fraction == "72091504":
            return {
                "01": {"composition_pct.C": {"operator": ">", "value": "0.4", "unit": "%"}},
                "02": {"mechanical_properties.yield_strength_mpa": {"operator": ">=", "value": "355", "unit": "MPa"}},
                "03": {"porcelain_exposed_parts": {"operator": "=", "value": True}},
                "99": {"qualifier": "other"},
            }.get(nico, {})
        if fraction == "72255091":
            expectations: dict[str, dict[str, object]] = {
                "01": {"B_min_pct": "0.0008", "thickness_mm": "1 < x < 3", "coiled": True, "tool_steel": False},
                "02": {"B_min_pct": "0.0008", "thickness_mm": "0.5 <= x <= 1", "coiled": True, "tool_steel": False},
                "03": {"B_min_pct": "0.0008", "thickness_mm": "x < 0.5", "coiled": True, "tool_steel": False},
                "04": {"B_min_pct": "0.0008", "thickness_mm": "3 <= x < 4.75", "coiled": True, "tool_steel": False},
                "05": {"B_min_pct": "0.0008", "thickness_mm": "x >= 4.75", "coiled": True, "tool_steel": False},
                "06": {"B_min_pct": "0.0008", "thickness_mm": "x < 4.75", "coiled": False, "tool_steel": False},
                "07": {"B_min_pct": "0.0008", "thickness_mm": "x >= 4.75", "coiled": False, "tool_steel": False},
                "08": {"high_speed_steel": True},
                "09": {"tool_steel": True},
                "10": {"porcelain_exposed_parts": True, "thickness_mm": "x >= 4.75"},
                "11": {"yield_strength_mpa": {"operator": ">=", "value": "355", "unit": "MPa"}},
                "91": {"qualifier": "other", "thickness_mm": "x >= 4.75"},
                "92": {"qualifier": "other", "porcelain_exposed_parts": True},
                "99": {"qualifier": "other"},
            }
            return expectations.get(nico, {})
        return {}

    @staticmethod
    def _nico_observations(
        facts: ProductFacts,
        fraction: str,
        nico: str,
    ) -> tuple[dict[str, object], tuple[str, ...]]:
        if fraction == "72091504":
            fields = {
                "01": ("composition_pct.C", facts.composition_pct.get("C")),
                "02": ("mechanical_properties.yield_strength_mpa", facts.yield_strength_mpa),
                "03": ("porcelain_exposed_parts", facts.porcelain_exposed_parts),
            }
            if nico in fields:
                field_path, value = fields[nico]
                return {field_path: str(value) if isinstance(value, Decimal) else value}, (field_path,)
            return {
                "composition_pct.C": (
                    str(facts.composition_pct.get("C"))
                    if facts.composition_pct.get("C") is not None else None
                ),
                "mechanical_properties.yield_strength_mpa": (
                    str(facts.yield_strength_mpa)
                    if facts.yield_strength_mpa is not None else None
                ),
                "porcelain_exposed_parts": facts.porcelain_exposed_parts,
            }, (
                "composition_pct.C",
                "mechanical_properties.yield_strength_mpa",
                "porcelain_exposed_parts",
            )
        if fraction == "72255091":
            if nico in {"01", "02", "03", "04", "05", "06", "07"}:
                return {
                    "composition_pct.B": (
                        str(facts.composition_pct.get("B"))
                        if facts.composition_pct.get("B") is not None else None
                    ),
                    "thickness_mm": str(facts.thickness_mm) if facts.thickness_mm is not None else None,
                    "coiled": facts.coiled,
                    "tool_steel": facts.tool_steel,
                }, ("composition_pct.B", "thickness_mm", "coiled", "tool_steel")
            if nico == "08":
                return {"high_speed_steel": facts.high_speed_steel}, ("high_speed_steel",)
            if nico == "09":
                return {"tool_steel": facts.tool_steel}, ("tool_steel",)
            if nico == "11":
                return {
                    "mechanical_properties.yield_strength_mpa": (
                        str(facts.yield_strength_mpa)
                        if facts.yield_strength_mpa is not None else None
                    )
                }, ("mechanical_properties.yield_strength_mpa",)
            if nico in {"10", "92"}:
                return {
                    "porcelain_exposed_parts": facts.porcelain_exposed_parts,
                    "thickness_mm": str(facts.thickness_mm) if facts.thickness_mm is not None else None,
                }, ("porcelain_exposed_parts", "thickness_mm")
            if nico == "91":
                return {
                    "thickness_mm": str(facts.thickness_mm) if facts.thickness_mm is not None else None
                }, ("thickness_mm",)
            return {
                "high_speed_steel": facts.high_speed_steel,
                "tool_steel": facts.tool_steel,
                "porcelain_exposed_parts": facts.porcelain_exposed_parts,
            }, ("high_speed_steel", "tool_steel", "porcelain_exposed_parts")
        return {
            "thickness_mm": str(facts.thickness_mm) if facts.thickness_mm is not None else None,
            "yield_strength_mpa": (
                str(facts.yield_strength_mpa) if facts.yield_strength_mpa is not None else None
            ),
        }, ("thickness_mm", "mechanical_properties.yield_strength_mpa")
