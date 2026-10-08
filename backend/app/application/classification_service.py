from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.classification_engine import Chapter72ClassificationEngine, ProductFacts
from backend.app.config import Settings
from backend.app.domain.enums import ApprovalStatus, RuleSetStatus
from backend.app.domain.errors import ApplicationError, NotFoundError
from backend.app.infrastructure.database.models import (
    ChemicalComposition,
    ClassificationResult,
    ClassificationRun,
    DecisionStep,
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
        rule_set = self._rule_set(session, rule_set_id)
        catalog_hash = rule_set.manifest_json.get("catalog_sha256")
        if not catalog_hash or catalog_hash.casefold() != self.engine.catalog.sha256.casefold():
            raise ApplicationError(
                "rule_catalog_mismatch",
                "La versión de reglas no coincide con el catálogo cargado",
                status_code=409,
            )
        parent = session.scalar(
            select(ClassificationRun)
            .where(ClassificationRun.certificate_id == certificate_id)
            .order_by(ClassificationRun.id.desc())
            .limit(1)
        )
        product_facts = [self._facts(session, product) for product in products]
        product_evidence = {
            product.id: self._evidence(session, product) for product in products
        }
        snapshot = {
            "certificate_id": certificate_id,
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
        for product, facts in zip(products, product_facts, strict=True):
            decision = self.engine.classify(facts)
            evidence = product_evidence[product.id]
            result = ClassificationResult(
                classification_run_id=run.id,
                product_id=product.id,
                product_type=decision.product_type,
                fraction=decision.fraction,
                nico=decision.nico,
                description=decision.description,
                outcome=decision.outcome.value,
                details_json={
                    "missing_fields": list(decision.missing_fields),
                    "candidates": list(decision.candidates),
                },
            )
            session.add(result)
            session.flush()
            for sequence, step in enumerate(decision.steps, start=1):
                session.add(
                    DecisionStep(
                        classification_result_id=result.id,
                        sequence=sequence,
                        rule_code=step.rule_code,
                        outcome=step.outcome.value,
                        input_json=step.inputs,
                        evidence_json=list(step.evidence) or evidence,
                        explanation=step.explanation,
                    )
                )
        return run

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
        superior = coating.get("superior_g_m2")
        inferior = coating.get("inferior_g_m2")
        if superior is not None or inferior is not None:
            both_sides = superior is not None and inferior is not None
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
        }

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
                "field_path": observation.field_path,
                "page_number": observation.page_number,
                "bbox": observation.bbox_json,
                "source_text": observation.source_text,
                "supersedes_id": observation.supersedes_id,
            }
            for observation in observations
        ]
