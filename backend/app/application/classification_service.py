from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.application.document_quality_service import DocumentQualityService
from backend.app.classification_engine import Chapter72ClassificationEngine, ProductFacts, source_reference
from backend.app.config import Settings
from backend.app.domain.enums import ApprovalStatus, RuleSetStatus
from backend.app.domain.errors import ApplicationError, NotFoundError
from backend.app.infrastructure.database.models import (
    ChemicalComposition,
    CandidateFactor,
    ClassificationCandidate,
    ClassificationResult,
    ClassificationRun,
    DecisionStep,
    EvidenceLink,
    MillCertificate,
    Observation,
    Product,
    RuleSet,
)


class ClassificationService:
    def __init__(
        self,
        settings: Settings,
        engine: Chapter72ClassificationEngine | None = None,
    ) -> None:
        self.settings = settings
        self.engine = engine or Chapter72ClassificationEngine()

    def classify_certificate(
        self,
        session: Session,
        *,
        certificate_id: int,
        person_name: str,
        reason: str,
        rule_set_id: int | None = None,
        source_run_id: int | None = None,
    ) -> ClassificationRun:
        person_name = person_name.strip()
        reason = reason.strip()
        if not person_name or not reason:
            raise ApplicationError(
                "audit_fields_required",
                "La persona y el motivo son obligatorios para reclasificar",
            )
        certificate = session.get(MillCertificate, certificate_id)
        if certificate is None:
            raise NotFoundError("Acta", certificate_id)
        products = session.scalars(
            select(Product)
            .where(Product.certificate_id == certificate_id)
            .order_by(Product.id)
        ).all()
        if not products:
            raise ApplicationError(
                "certificate_has_no_products",
                "El acta todavía no contiene productos clasificables",
                status_code=409,
            )
        source_run = None
        if source_run_id is not None:
            source_run = session.get(ClassificationRun, source_run_id)
            if source_run is None or source_run.certificate_id != certificate_id:
                raise NotFoundError("Ejecución de clasificación", source_run_id)
            if rule_set_id is not None and rule_set_id != source_run.rule_set_id:
                raise ApplicationError(
                    "historical_rule_set_mismatch",
                    "La reproducción histórica debe usar el conjunto de reglas original",
                    status_code=409,
                )
            rule_set = session.get(RuleSet, source_run.rule_set_id)
            if rule_set is None:
                raise NotFoundError("Conjunto de reglas", source_run.rule_set_id)
            if source_run.input_snapshot_json.get("engine_sha256") != self.engine.source_sha256:
                raise ApplicationError(
                    "historical_engine_unavailable",
                    "La versión exacta del motor histórico no está disponible",
                    status_code=409,
                )
        else:
            rule_set = self._rule_set(session, rule_set_id)
        catalog_hash = rule_set.manifest_json.get("catalog_sha256")
        if not catalog_hash or catalog_hash.casefold() != self.engine.catalog.sha256.casefold():
            raise ApplicationError(
                "rule_catalog_mismatch",
                "La versión de reglas no coincide con el catálogo cargado",
                status_code=409,
            )
        parent = source_run or session.scalar(
            select(ClassificationRun)
            .where(ClassificationRun.certificate_id == certificate_id)
            .order_by(ClassificationRun.id.desc())
            .limit(1)
        )
        if source_run is None:
            product_facts = [self._facts(session, product) for product in products]
            product_evidence = {
                product.id: self._evidence(session, product) for product in products
            }
        else:
            snapshots = source_run.input_snapshot_json.get("products", [])
            by_id = {str(item.get("product_id")): item for item in snapshots}
            if set(by_id) != {str(product.id) for product in products}:
                raise ApplicationError(
                    "historical_snapshot_mismatch",
                    "La instantánea histórica no coincide con los productos del acta",
                    status_code=409,
                )
            product_facts = [self._facts_from_snapshot(by_id[str(product.id)]) for product in products]
            product_evidence = {
                product.id: list(by_id[str(product.id)].get("evidence") or [])
                for product in products
            }
        snapshot = {
            "certificate_id": certificate_id,
            "engine_sha256": self.engine.source_sha256,
            "person_name": person_name,
            "reason": reason,
            "workstation_name": self.settings.workstation_name,
            "products": [
                {
                    **self._snapshot(facts),
                    "evidence": product_evidence[product.id],
                }
                for product, facts in zip(products, product_facts, strict=True)
            ],
        }
        run = ClassificationRun(
            certificate_id=certificate_id,
            rule_set_id=rule_set.id,
            parent_run_id=parent.id if parent else None,
            approval_status=ApprovalStatus.NEEDS_REVIEW.value,
            input_snapshot_json=snapshot,
            demo_notice=self.settings.demo_notice,
        )
        certificate.approval_status = ApprovalStatus.NEEDS_REVIEW.value
        session.add(run)
        session.flush()
        quality_service = DocumentQualityService(self.settings)
        quality_report = quality_service.evaluate_certificate(session, certificate_id)
        if quality_report.blocking_count > 0:
            certificate.approval_status = ApprovalStatus.NEEDS_REVIEW.value

        for product, facts in zip(products, product_facts, strict=True):
            evidence = product_evidence[product.id]
            prod_issues = [
                issue.as_dict()
                for issue in quality_report.issues
                if (
                    issue.entity_identifier in (str(product.id), product.product_identifier)
                    or (issue.scope == "heat" and str(product.heat_id) == str(issue.entity_identifier))
                    or issue.scope == "certificate"
                )
            ]
            has_blocking = any(i["severity"] == "blocking" for i in prod_issues)
            decision = self.engine.classify(facts)

            result = ClassificationResult(
                classification_run_id=run.id,
                product_id=product.id,
                product_type=decision.product_type,
                fraction=decision.fraction,
                nico=decision.nico,
                description=decision.description,
                outcome="needs_review" if has_blocking else decision.outcome.value,
                details_json={
                    "missing_fields": list(decision.missing_fields),
                    "candidates": list(decision.candidates),
                    "valid_candidate_count": len(decision.ranked_candidates),
                    "selection_required": bool(decision.ranked_candidates),
                    "quality_issues": prod_issues,
                    "quality_score": quality_report.quality_score,
                    "document_quality_status": quality_report.status,
                    "discarded_candidates": [
                        {
                            "fraction": candidate.fraction,
                            "nico": candidate.nico,
                            "reason_code": candidate.reason_code,
                            "explanation": candidate.explanation,
                        }
                        for candidate in decision.discarded_candidates
                    ],
                },
            )
            session.add(result)
            session.flush()
            for candidate in decision.ranked_candidates:
                    candidate_row = ClassificationCandidate(
                        classification_result_id=result.id,
                        rank=candidate.rank,
                        fraction=candidate.fraction,
                        nico=candidate.nico,
                        description=candidate.description,
                        support_level=candidate.support_level,
                        details_json={
                            "missing_fields": list(candidate.missing_fields),
                            "conflicts": list(candidate.conflicts),
                        },
                    )
                    session.add(candidate_row)
                    session.flush()
                    for factor in candidate.factors:
                        factor_row = CandidateFactor(
                            candidate_id=candidate_row.id,
                            sequence=factor.sequence,
                            rule_code=factor.rule_code,
                            outcome=factor.outcome.value,
                            operator=factor.operator,
                            expected_json=factor.expected,
                            observed_json=factor.observed,
                            unit=factor.unit,
                            explanation=factor.explanation,
                            required_for_selection=factor.required_for_selection,
                        )
                        session.add(factor_row)
                        session.flush()
                        exact_evidence = self._step_evidence(evidence, factor.evidence_fields)
                        for item in exact_evidence:
                            session.add(EvidenceLink(
                                decision_step_id=None,
                                candidate_factor_id=factor_row.id,
                                observation_id=item["observation_id"],
                                source_type="observation",
                                field_path=item["field_path"],
                                source_reference_json={},
                            ))
                        session.add(EvidenceLink(
                            decision_step_id=None,
                            candidate_factor_id=factor_row.id,
                            observation_id=None,
                            source_type="rule_source",
                            field_path=None,
                            source_reference_json=self._candidate_rule_reference(
                                rule_set, factor, candidate
                            ),
                        ))
            for sequence, step in enumerate(decision.steps, start=1):
                exact_evidence = self._step_evidence(evidence, step.evidence_fields)
                decision_step = DecisionStep(
                    classification_result_id=result.id,
                    sequence=sequence,
                    rule_code=step.rule_code,
                    outcome=step.outcome.value,
                    input_json=step.inputs,
                    evidence_json=list(step.evidence) or exact_evidence,
                    explanation=step.explanation,
                )
                session.add(decision_step)
                session.flush()
                for item in exact_evidence:
                    session.add(EvidenceLink(
                        decision_step_id=decision_step.id,
                        observation_id=item["observation_id"],
                        source_type="observation",
                        field_path=item["field_path"],
                        source_reference_json={},
                    ))
                session.add(EvidenceLink(
                    decision_step_id=decision_step.id,
                    observation_id=None,
                    source_type="rule_source",
                    field_path=None,
                    source_reference_json=self._rule_reference(rule_set, step),
                ))
        return run

    def _rule_reference(
        self,
        rule_set: RuleSet,
        step,
    ) -> dict[str, Any]:
        reference: dict[str, Any] = {
            "rule_set_id": rule_set.id,
            "rule_set_name": rule_set.name,
            "rule_set_version": rule_set.version,
            "source_hash": rule_set.source_hash,
            "rule_code": step.rule_code,
            "source": rule_set.manifest_json.get("source"),
        }
        fraction = step.inputs.get("fraction")
        nico = step.inputs.get("nico")
        if fraction:
            entry = self.engine.catalog.get(f"{fraction}{nico}" if nico else fraction)
            if entry is not None:
                reference["catalog_page"] = entry.page
                reference["catalog_code"] = entry.code
        reference.update(source_reference(self.engine.catalog, step.rule_code, fraction, nico, step.evidence_fields, rule_set.source_hash))
        return reference

    def _candidate_rule_reference(
        self,
        rule_set: RuleSet,
        factor,
        candidate,
    ) -> dict[str, Any]:
        reference: dict[str, Any] = {
            "rule_set_id": rule_set.id,
            "rule_set_name": rule_set.name,
            "rule_set_version": rule_set.version,
            "source_hash": rule_set.source_hash,
            "rule_code": factor.rule_code,
            "source": rule_set.manifest_json.get("source"),
        }
        entry = self.engine.catalog.get(f"{candidate.fraction}{candidate.nico}")
        if entry is not None:
            reference["catalog_page"] = entry.page
            reference["catalog_code"] = entry.code
        reference.update(source_reference(self.engine.catalog, factor.rule_code, candidate.fraction, candidate.nico, factor.evidence_fields, rule_set.source_hash))
        return reference

    @staticmethod
    def _step_evidence(
        evidence: list[dict[str, Any]], field_paths: tuple[str, ...]
    ) -> list[dict[str, Any]]:
        selected: list[dict[str, Any]] = []
        for field_path in dict.fromkeys(field_paths):
            matches = [item for item in evidence if item["field_path"] == field_path]
            if not matches:
                continue
            best = max(
                matches,
                key=lambda item: (
                    item["page_number"] is not None,
                    item["bbox"] is not None,
                    item["product_id"] is not None,
                    item["observation_id"],
                ),
            )
            selected.append(best)
        return selected

    @staticmethod
    def _rule_set(session: Session, rule_set_id: int | None) -> RuleSet:
        if rule_set_id is not None:
            rule_set = session.get(RuleSet, rule_set_id)
            if rule_set is None:
                raise NotFoundError("Conjunto de reglas", rule_set_id)
            if rule_set.status == RuleSetStatus.RETIRED.value:
                raise ApplicationError(
                    "rule_set_retired",
                    "El conjunto de reglas seleccionado está retirado",
                    status_code=409,
                )
            return rule_set
        rule_set = session.scalar(
            select(RuleSet)
            .where(RuleSet.status.in_([RuleSetStatus.APPROVED.value, RuleSetStatus.DRAFT.value]))
            .order_by(
                (RuleSet.status == RuleSetStatus.APPROVED.value).desc(),
                RuleSet.id.desc(),
            )
            .limit(1)
        )
        if rule_set is None:
            raise ApplicationError(
                "rule_set_unavailable",
                "No existe un conjunto de reglas disponible",
                status_code=409,
            )
        return rule_set

    @staticmethod
    def _facts(session: Session, product: Product) -> ProductFacts:
        chemistry_rows = session.scalars(
            select(ChemicalComposition).where(
                (ChemicalComposition.product_id == product.id)
                | (
                    (ChemicalComposition.product_id.is_(None))
                    & (ChemicalComposition.heat_id == product.heat_id)
                )
            )
        ).all()
        composition = {row.element: row.percentage for row in chemistry_rows}
        properties = product.properties_json or {}
        mechanical = dict(properties.get("mechanical_properties") or {})
        coating = dict(properties.get("coating") or {})
        current_observations = session.scalars(
            select(Observation)
            .where(
                Observation.is_current.is_(True),
                (Observation.product_id == product.id)
                | (
                    (Observation.product_id.is_(None))
                    & (Observation.heat_id == product.heat_id)
                ),
            )
            .order_by(Observation.product_id.is_not(None), Observation.id)
        ).all()
        current_values = {
            observation.field_path: observation.normalized_value_json
            for observation in current_observations
        }
        for field_path, value in current_values.items():
            if field_path.startswith("composition_pct."):
                composition[field_path.removeprefix("composition_pct.")] = (
                    ClassificationService._decimal(value)
                )
            elif field_path.startswith("mechanical_properties."):
                mechanical[field_path.removeprefix("mechanical_properties.")] = value
            elif field_path.startswith("coating."):
                coating[field_path.removeprefix("coating.")] = value
        condition_value = properties.get("condition") or []
        condition_items = [condition_value] if isinstance(condition_value, str) else condition_value
        condition = {str(item).casefold() for item in condition_items}
        both_sides = None
        superior = ClassificationService._decimal(coating.get("superior_g_m2"))
        inferior = ClassificationService._decimal(coating.get("inferior_g_m2"))
        if superior == 0 or inferior == 0:
            both_sides = False
        elif superior is not None and inferior is not None:
            both_sides = superior > 0 and inferior > 0
        return ProductFacts(
            product_id=product.id,
            form=current_values.get("form", product.form),
            coiled=current_values.get("coiled", product.coiled),
            rolling=current_values.get("rolling", product.rolling),
            width_mm=ClassificationService._decimal(
                current_values.get("width_mm", product.width_mm)
            ),
            thickness_mm=ClassificationService._decimal(
                current_values.get("thickness_mm", product.thickness_mm)
            ),
            composition_pct=composition,
            coated=current_values.get(
                "coated", True if coating.get("metal") else properties.get("coated")
            ),
            coating_metal=coating.get("metal"),
            coating_process=coating.get("process"),
            coating_both_sides=both_sides,
            yield_strength_mpa=ClassificationService._decimal(
                mechanical.get("yield_strength_mpa")
            ),
            pickled=current_values.get(
                "pickled",
                True if condition & {"pickled", "decapado"}
                else False if condition & {"not_pickled", "unpickled", "sin decapar"}
                else None,
            ),
            pattern_in_relief=current_values.get(
                "pattern_in_relief", properties.get("pattern_in_relief")
            ),
            porcelain_exposed_parts=current_values.get(
                "porcelain_exposed_parts", properties.get("porcelain_exposed_parts")
            ),
            pipeline_steel=current_values.get(
                "pipeline_steel", properties.get("pipeline_steel")
            ),
            high_speed_steel=current_values.get(
                "high_speed_steel", properties.get("high_speed_steel")
            ),
            tool_steel=current_values.get(
                "tool_steel", properties.get("tool_steel")
            ),
            grain_oriented=current_values.get(
                "grain_oriented", properties.get("grain_oriented")
            ),
            magnetic_silicon=current_values.get(
                "magnetic_silicon", properties.get("magnetic_silicon")
            ),
            stainless_series=current_values.get(
                "stainless_series", properties.get("stainless_series")
            ),
            rolled_four_faces=current_values.get(
                "rolled_four_faces", properties.get("rolled_four_faces")
            ),
            clad=current_values.get(
                "clad", properties.get("clad")
            ),
            temper=current_values.get(
                "temper", properties.get("temper")
            ),
            magnetic_loss_w_per_kg=ClassificationService._decimal(current_values.get(
                "magnetic_loss_w_per_kg", properties.get("magnetic_loss_w_per_kg")
            )),
            magnetic_induction_tesla=ClassificationService._decimal(current_values.get(
                "magnetic_induction_tesla", properties.get("magnetic_induction_tesla")
            )),
            secondary_reduction_ratio=ClassificationService._decimal(current_values.get(
                "secondary_reduction_ratio", properties.get("secondary_reduction_ratio")
            )),
            can_body_end_use=current_values.get(
                "can_body_end_use", properties.get("can_body_end_use")
            ),
            deep_drawing_class=current_values.get(
                "deep_drawing_class", properties.get("deep_drawing_class")
            ),
            cladding_weight_percentage=ClassificationService._decimal(current_values.get(
                "cladding_weight_percentage", properties.get("cladding_weight_percentage")
            )),
        )

    @staticmethod
    def _decimal(value: Any) -> Decimal | None:
        return None if value is None else Decimal(str(value))

    @staticmethod
    def _snapshot(facts: ProductFacts) -> dict[str, Any]:
        return {
            "product_id": facts.product_id,
            "form": facts.form,
            "coiled": facts.coiled,
            "rolling": facts.rolling,
            "width_mm": str(facts.width_mm) if facts.width_mm is not None else None,
            "thickness_mm": str(facts.thickness_mm) if facts.thickness_mm is not None else None,
            "composition_pct": {
                key: str(value) if value is not None else None
                for key, value in sorted(facts.composition_pct.items())
            },
            "coated": facts.coated,
            "coating_metal": facts.coating_metal,
            "coating_process": facts.coating_process,
            "coating_both_sides": facts.coating_both_sides,
            "yield_strength_mpa": (
                str(facts.yield_strength_mpa)
                if facts.yield_strength_mpa is not None else None
            ),
            "pickled": facts.pickled,
            "pattern_in_relief": facts.pattern_in_relief,
            "porcelain_exposed_parts": facts.porcelain_exposed_parts,
            "pipeline_steel": facts.pipeline_steel,
            "high_speed_steel": facts.high_speed_steel,
            "tool_steel": facts.tool_steel,
            "grain_oriented": facts.grain_oriented,
            "magnetic_silicon": facts.magnetic_silicon,
            "stainless_series": facts.stainless_series,
            "rolled_four_faces": facts.rolled_four_faces,
            "clad": facts.clad,
            "temper": facts.temper,
            "magnetic_loss_w_per_kg": ClassificationService._decimal_text(facts.magnetic_loss_w_per_kg),
            "magnetic_induction_tesla": ClassificationService._decimal_text(facts.magnetic_induction_tesla),
            "secondary_reduction_ratio": ClassificationService._decimal_text(facts.secondary_reduction_ratio),
            "can_body_end_use": facts.can_body_end_use,
            "deep_drawing_class": facts.deep_drawing_class,
            "cladding_weight_percentage": ClassificationService._decimal_text(facts.cladding_weight_percentage),
        }

    @staticmethod
    def _decimal_text(value: Decimal | None) -> str | None:
        return str(value) if value is not None else None

    @staticmethod
    def _facts_from_snapshot(snapshot: dict[str, Any]) -> ProductFacts:
        decimal_fields = {
            "width_mm", "thickness_mm", "yield_strength_mpa",
            "magnetic_loss_w_per_kg", "magnetic_induction_tesla",
            "secondary_reduction_ratio", "cladding_weight_percentage",
        }
        values = {
            field: ClassificationService._decimal(snapshot.get(field))
            if field in decimal_fields else snapshot.get(field)
            for field in ProductFacts.__dataclass_fields__
            if field != "composition_pct"
        }
        values["composition_pct"] = {
            key: ClassificationService._decimal(value)
            for key, value in (snapshot.get("composition_pct") or {}).items()
        }
        return ProductFacts(**values)

    @staticmethod
    def _evidence(session: Session, product: Product) -> list[dict[str, Any]]:
        observations = session.scalars(
            select(Observation)
            .where(
                Observation.is_current.is_(True),
                (Observation.product_id == product.id)
                | (
                    (Observation.product_id.is_(None))
                    & (Observation.heat_id == product.heat_id)
                ),
            )
            .order_by(Observation.id)
        ).all()
        return [
            {
                "observation_id": observation.id,
                "heat_id": observation.heat_id,
                "product_id": observation.product_id,
                "field_path": observation.field_path,
                "raw_value": observation.raw_value_json,
                "normalized_value": observation.normalized_value_json,
                "unit": observation.unit,
                "confidence": observation.confidence,
                "page_number": observation.page_number,
                "bbox": observation.bbox_json,
                "source_text": observation.source_text,
                "supersedes_id": observation.supersedes_id,
            }
            for observation in observations
        ]
