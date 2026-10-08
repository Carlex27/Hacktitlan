from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.config import Settings
from backend.app.domain.enums import ApprovalStatus
from backend.app.domain.errors import ApplicationError, ConflictError, NotFoundError
from backend.app.infrastructure.database.models import (
    ApprovalEvent,
    CandidateFactor,
    ChemicalComposition,
    ClassificationCandidate,
    ClassificationResult,
    ClassificationRun,
    ClassificationSelection,
    Correction,
    MillCertificate,
    Observation,
    Heat,
    Product,
)


class ReviewService:
    allowed_manual_fields = {
        "form", "coiled", "coated", "rolling", "width_mm", "thickness_mm",
        "mechanical_properties.yield_strength_mpa",
        "coating.metal", "coating.process", "coating.superior_g_m2",
        "coating.inferior_g_m2", "pickled", "pattern_in_relief",
        "porcelain_exposed_parts", "pipeline_steel",
        "high_speed_steel", "tool_steel",
    }

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def correct_observation(
        self,
        session: Session,
        *,
        observation_id: int,
        normalized_value: Any,
        raw_value: Any,
        unit: str | None,
        person_name: str,
        reason: str,
    ) -> Observation:
        person_name, reason = self._require_actor_reason(person_name, reason)
        previous = session.get(Observation, observation_id)
        if previous is None:
            raise NotFoundError("Observación", observation_id)
        if not previous.is_current:
            raise ConflictError("observation_superseded", "La observación ya fue reemplazada")
        self._validate_normalized(previous.field_path, normalized_value)
        previous.is_current = False
        replacement = Observation(
            certificate_id=previous.certificate_id,
            heat_id=previous.heat_id,
            product_id=previous.product_id,
            field_path=previous.field_path,
            raw_value_json=raw_value,
            normalized_value_json=normalized_value,
            unit=unit,
            confidence=1.0,
            page_number=previous.page_number,
            bbox_json=previous.bbox_json,
            source_text="correccion_manual",
            inherited=False,
            supersedes_id=previous.id,
            is_current=True,
        )
        session.add(replacement)
        session.flush()
        session.add(
            Correction(
                certificate_id=previous.certificate_id,
                previous_observation_id=previous.id,
                replacement_observation_id=replacement.id,
                person_name=person_name,
                reason=reason,
                workstation_name=self.settings.workstation_name,
            )
        )
        self._sync_entity_field(
            session,
            product_id=previous.product_id,
            heat_id=previous.heat_id,
            field_path=previous.field_path,
            normalized_value=normalized_value,
            raw_value=raw_value,
        )
        return replacement

    def add_manual_observation(
        self,
        session: Session,
        *,
        certificate_id: int,
        product_id: int | None,
        heat_id: int | None,
        field_path: str,
        normalized_value: Any,
        raw_value: Any,
        unit: str | None,
        person_name: str,
        reason: str,
    ) -> Observation:
        person_name, reason = self._require_actor_reason(person_name, reason)
        field_path = field_path.strip()
        is_composition = bool(re.fullmatch(r"composition_pct\.[A-Za-z][A-Za-z0-9_]{0,49}", field_path))
        if not (
            field_path in self.allowed_manual_fields
            or is_composition
        ):
            raise ApplicationError(
                "manual_field_not_allowed",
                "El campo no está habilitado para captura manual",
            )
        self._validate_normalized(field_path, normalized_value)
        certificate = session.get(MillCertificate, certificate_id)
        if certificate is None:
            raise NotFoundError("Acta", certificate_id)
        if product_id is not None:
            product = session.get(Product, product_id)
            if product is None or product.certificate_id != certificate_id:
                raise NotFoundError("Producto del acta", product_id)
            heat_id = product.heat_id
        elif heat_id is not None:
            heat = session.get(Heat, heat_id)
            if heat is None or heat.certificate_id != certificate_id:
                raise NotFoundError("Colada del acta", heat_id)
        else:
            raise ApplicationError(
                "observation_scope_required",
                "La observación manual requiere producto o colada",
            )
        existing = session.scalar(
            select(Observation).where(
                Observation.certificate_id == certificate_id,
                Observation.product_id == product_id,
                Observation.heat_id == heat_id,
                Observation.field_path == field_path,
                Observation.is_current.is_(True),
            )
        )
        if existing is not None:
            raise ConflictError(
                "observation_already_exists",
                "El campo ya existe; debe corregirse mediante su observation_id",
            )
        observation = Observation(
            certificate_id=certificate_id,
            heat_id=heat_id,
            product_id=product_id,
            field_path=field_path,
            raw_value_json=raw_value,
            normalized_value_json=normalized_value,
            unit=unit,
            confidence=1.0,
            inherited=False,
            is_current=True,
            source_text="captura_manual",
        )
        session.add(observation)
        session.flush()
        session.add(
            Correction(
                certificate_id=certificate_id,
                previous_observation_id=None,
                replacement_observation_id=observation.id,
                person_name=person_name,
                reason=reason,
                workstation_name=self.settings.workstation_name,
            )
        )
        self._sync_entity_field(
            session,
            product_id=product_id,
            heat_id=heat_id,
            field_path=field_path,
            normalized_value=normalized_value,
            raw_value=raw_value,
        )
        return observation

    def transition_classification(
        self,
        session: Session,
        *,
        run_id: int,
        target: ApprovalStatus,
        person_name: str,
        reason: str,
    ) -> ClassificationRun:
        person_name, reason = self._require_actor_reason(person_name, reason)
        run = session.get(ClassificationRun, run_id)
        if run is None:
            raise NotFoundError("Ejecución de clasificación", run_id)
        current = ApprovalStatus(run.approval_status)
        if target is ApprovalStatus.APPROVED:
            results = session.scalars(
                select(ClassificationResult).where(
                    ClassificationResult.classification_run_id == run.id
                )
            ).all()
            selected_result_ids = set(session.scalars(
                select(ClassificationSelection.classification_result_id)
                .where(ClassificationSelection.classification_result_id.in_(
                    [result.id for result in results]
                ))
                .distinct()
            ).all())
            if not results or any(
                result.id not in selected_result_ids
                or result.outcome != "classified"
                or result.fraction is None
                or result.nico is None
                for result in results
            ):
                raise ConflictError(
                    "classification_incomplete",
                    "No se puede aprobar una ejecución sin una selección autorizada para cada producto",
                )
            for result in results:
                selected_candidate_id = (result.details_json or {}).get("selected_candidate_id")
                if selected_candidate_id is not None:
                    candidate = session.get(ClassificationCandidate, selected_candidate_id)
                    if candidate is not None:
                        missing = list((candidate.details_json or {}).get("missing_fields") or [])
                        conflicts = list((candidate.details_json or {}).get("conflicts") or [])
                        if missing or conflicts:
                            raise ConflictError(
                                "classification_incomplete",
                                "No se puede aprobar una opción con datos obligatorios faltantes o contradicciones",
                            )
        allowed = {
            ApprovalStatus.DRAFT: {ApprovalStatus.NEEDS_REVIEW, ApprovalStatus.APPROVED, ApprovalStatus.REJECTED},
            ApprovalStatus.NEEDS_REVIEW: {ApprovalStatus.APPROVED, ApprovalStatus.REJECTED},
            ApprovalStatus.REJECTED: {ApprovalStatus.NEEDS_REVIEW, ApprovalStatus.APPROVED},
            ApprovalStatus.APPROVED: {ApprovalStatus.REJECTED},
        }
        if target not in allowed[current]:
            raise ConflictError(
                "invalid_approval_transition",
                f"No se puede cambiar de {current.value} a {target.value}",
            )
        run.approval_status = target.value
        latest_run_id = session.scalar(
            select(func.max(ClassificationRun.id)).where(
                ClassificationRun.certificate_id == run.certificate_id
            )
        )
        if latest_run_id == run.id:
            certificate = session.get(MillCertificate, run.certificate_id)
            if certificate is not None:
                certificate.approval_status = target.value
        session.add(
            ApprovalEvent(
                classification_run_id=run.id,
                from_status=current.value,
                to_status=target.value,
                person_name=person_name,
                reason=reason,
                workstation_name=self.settings.workstation_name,
            )
        )
        return run

    def select_classification_candidate(
        self,
        session: Session,
        *,
        result_id: int,
        candidate_id: int,
        person_name: str,
        reason: str,
    ) -> ClassificationSelection:
        person_name, reason = self._require_actor_reason(person_name, reason)
        result = session.scalar(
            select(ClassificationResult)
            .where(ClassificationResult.id == result_id)
            .with_for_update()
        )
        if result is None:
            raise NotFoundError("Resultado de clasificación", result_id)
        candidate = session.get(ClassificationCandidate, candidate_id)
        if candidate is None or candidate.classification_result_id != result.id:
            raise ConflictError(
                "candidate_result_mismatch",
                "La opción no pertenece al resultado indicado",
            )
        conflicts = list((candidate.details_json or {}).get("conflicts") or [])
        blocking_factor = session.scalar(
            select(CandidateFactor.id)
            .where(
                CandidateFactor.candidate_id == candidate.id,
                CandidateFactor.required_for_selection.is_(True),
                CandidateFactor.outcome.in_(["not_matched", "conflict"]),
            )
            .limit(1)
        )
        if conflicts or blocking_factor is not None:
            raise ConflictError(
                "candidate_has_conflicts",
                "La opción contiene contradicciones y no puede seleccionarse",
            )
        candidates = session.scalars(
            select(ClassificationCandidate)
            .where(ClassificationCandidate.classification_result_id == result.id)
            .order_by(ClassificationCandidate.rank)
        ).all()
        if len(candidates) != 3 or [item.rank for item in candidates] != [1, 2, 3]:
            raise ConflictError(
                "three_valid_candidates_required",
                "La selección requiere exactamente tres opciones válidas",
            )
        previous = session.scalar(
            select(ClassificationSelection)
            .where(ClassificationSelection.classification_result_id == result.id)
            .order_by(ClassificationSelection.id.desc())
            .limit(1)
        )
        selection = ClassificationSelection(
            classification_result_id=result.id,
            candidate_id=candidate.id,
            supersedes_selection_id=previous.id if previous else None,
            person_name=person_name,
            reason=reason,
            workstation_name=self.settings.workstation_name,
        )
        session.add(selection)
        result.fraction = candidate.fraction
        result.nico = candidate.nico
        result.description = candidate.description
        result.outcome = "classified"
        details = dict(result.details_json or {})
        details.update({
            "selected_candidate_id": candidate.id,
            "selection_required": False,
        })
        result.details_json = details
        session.flush()
        return selection

    @staticmethod
    def _require_actor_reason(person_name: str, reason: str) -> tuple[str, str]:
        person_name = person_name.strip()
        reason = reason.strip()
        if not person_name or not reason:
            raise ApplicationError(
                "audit_fields_required",
                "La persona y el motivo son obligatorios",
            )
        return person_name, reason

    @staticmethod
    def _validate_normalized(field_path: str, value: Any) -> None:
        # Corrections may explicitly revoke an unreliable value; unknown is null.
        if value is None:
            return
        boolean_fields = {
            "coiled", "coated", "pickled", "pattern_in_relief",
            "porcelain_exposed_parts", "pipeline_steel",
            "high_speed_steel", "tool_steel",
        }
        if field_path in boolean_fields:
            if not isinstance(value, bool):
                raise ApplicationError(
                    "invalid_observation_value", "El campo requiere true o false"
                )
            return
        if field_path == "rolling":
            if value not in {"hot", "cold"}:
                raise ApplicationError(
                    "invalid_observation_value", "rolling debe ser hot o cold"
                )
            return
        numeric = (
            field_path in {
                "width_mm", "thickness_mm",
                "mechanical_properties.yield_strength_mpa",
                "coating.superior_g_m2", "coating.inferior_g_m2",
            }
            or field_path.startswith("composition_pct.")
        )
        if not numeric:
            return
        try:
            number = Decimal(str(value))
        except (InvalidOperation, ValueError) as exc:
            raise ApplicationError(
                "invalid_observation_value", "El campo requiere un número"
            ) from exc
        if not number.is_finite():
            raise ApplicationError(
                "invalid_observation_value", "El número debe ser finito"
            )
        if number < 0:
            raise ApplicationError(
                "invalid_observation_value", "El valor no puede ser negativo"
            )
        if field_path.startswith("composition_pct.") and number > 100:
            raise ApplicationError(
                "invalid_observation_value", "El porcentaje no puede exceder 100"
            )

    def _sync_entity_field(
        self,
        session: Session,
        *,
        product_id: int | None,
        heat_id: int | None,
        field_path: str,
        normalized_value: Any,
        raw_value: Any,
    ) -> None:
        if product_id is not None:
            product = session.get(Product, product_id)
            if product is not None:
                if field_path == "thickness_mm":
                    product.thickness_mm = (
                        Decimal(str(normalized_value)) if normalized_value is not None else None
                    )
                elif field_path == "width_mm":
                    product.width_mm = (
                        Decimal(str(normalized_value)) if normalized_value is not None else None
                    )
                elif field_path == "length_m":
                    product.length_m = (
                        Decimal(str(normalized_value)) if normalized_value is not None else None
                    )
                elif field_path == "weight_kg":
                    product.weight_kg = (
                        Decimal(str(normalized_value)) if normalized_value is not None else None
                    )
                elif field_path == "form":
                    product.form = str(normalized_value) if normalized_value is not None else None
                elif field_path == "coiled":
                    product.coiled = bool(normalized_value) if normalized_value is not None else None
                elif field_path == "rolling":
                    product.rolling = str(normalized_value) if normalized_value is not None else None

        if field_path.startswith("composition_pct."):
            elem = field_path.split(".", 1)[1]
            comp = session.scalar(
                select(ChemicalComposition).where(
                    ChemicalComposition.product_id == product_id,
                    ChemicalComposition.heat_id == heat_id,
                    ChemicalComposition.element == elem,
                )
            )
            val = (
                Decimal(str(normalized_value))
                if normalized_value is not None
                else None
            )
            if comp is not None:
                comp.percentage = val
                comp.raw_value_json = raw_value
            else:
                session.add(
                    ChemicalComposition(
                        product_id=product_id,
                        heat_id=heat_id,
                        element=elem,
                        percentage=val,
                        raw_value_json=raw_value,
                        inherited=False,
                    )
                )

