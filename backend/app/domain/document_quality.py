"""Document quality validation, anomaly detection, confidence calculation, and product family requirements."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum
from typing import Any


class QualityCategory(StrEnum):
    MISSING = "missing"
    LOW_CONFIDENCE = "low_confidence"
    CONTRADICTION = "contradiction"
    ANOMALY = "anomaly"


class QualitySeverity(StrEnum):
    BLOCKING = "blocking"
    WARNING = "warning"


class ProductFamily(StrEnum):
    FLAT_ROLLED_COIL = "flat_rolled_coil"
    FLAT_ROLLED_PLATE = "flat_rolled_plate"
    FLAT_ROLLED_GENERAL = "flat_rolled_general"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class QualityIssue:
    code: str
    category: QualityCategory
    severity: QualitySeverity
    scope: str  # "certificate", "heat", "product"
    field_path: str
    message: str
    entity_identifier: str | None = None
    raw_value: Any | None = None
    normalized_value: Any | None = None
    confidence: float | None = None
    page_number: int | None = None
    bbox: dict[str, Any] | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "category": self.category.value,
            "severity": self.severity.value,
            "scope": self.scope,
            "entity_identifier": self.entity_identifier,
            "field_path": self.field_path,
            "message": self.message,
            "raw_value": self.raw_value,
            "normalized_value": (
                str(self.normalized_value)
                if isinstance(self.normalized_value, Decimal)
                else self.normalized_value
            ),
            "confidence": self.confidence,
            "page_number": self.page_number,
            "bbox": self.bbox,
        }


@dataclass(frozen=True)
class DocumentQualityReport:
    certificate_id: int | None
    status: str  # "clean" | "needs_review"
    quality_score: float  # 0.0 to 1.0
    product_family: ProductFamily
    issues: tuple[QualityIssue, ...]
    provenance_summary: dict[str, int] = field(default_factory=dict)
    blocking_count: int = 0
    warning_count: int = 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "certificate_id": self.certificate_id,
            "status": self.status,
            "quality_score": round(self.quality_score, 4),
            "product_family": self.product_family.value,
            "blocking_count": self.blocking_count,
            "warning_count": self.warning_count,
            "provenance_summary": dict(self.provenance_summary),
            "issues": [issue.as_dict() for issue in self.issues],
        }


CONFIDENCE_THRESHOLD_MIN = 0.70

VALID_DIMENSION_UNITS = {"mm", "milimetros", "m", "metros", "kg", "kilogramos", "ton", "t"}
VALID_CHEMISTRY_UNITS = {"%", "wt%", "mass%", "ppm", None}


def detect_product_family(product: dict[str, Any] | Any) -> ProductFamily:
    coiled = (
        product.get("coiled")
        if isinstance(product, dict)
        else getattr(product, "coiled", None)
    )
    form = (
        (product.get("form") or "").lower()
        if isinstance(product, dict)
        else (getattr(product, "form", "") or "").lower()
    )

    if coiled is True or any(k in form for k in ("coil", "rollo", "bobina")):
        return ProductFamily.FLAT_ROLLED_COIL
    if coiled is False or any(k in form for k in ("plate", "placa", "sheet", "hoja", "chapa")):
        return ProductFamily.FLAT_ROLLED_PLATE
    return ProductFamily.FLAT_ROLLED_GENERAL


def validate_document_quality(
    *,
    certificate_id: int | None,
    document_metadata: dict[str, Any],
    products: list[dict[str, Any]],
    heats: list[dict[str, Any]],
    observations: list[dict[str, Any]],
    compositions: list[dict[str, Any]],
) -> DocumentQualityReport:
    """Evaluate document completeness, confidence, physical consistency, and scope integrity."""
    issues: list[QualityIssue] = []
    provenance_counts: dict[str, int] = {
        "digital_text": 0,
        "ocr_text": 0,
        "inherited": 0,
        "manual_capture": 0,
        "unknown": 0,
    }

    # 1. Certificate-level metadata checks
    cert_no = document_metadata.get("certificate_no")
    if not cert_no or str(cert_no).strip() == "":
        issues.append(QualityIssue(
            code="missing_certificate_number",
            category=QualityCategory.MISSING,
            severity=QualitySeverity.BLOCKING,
            scope="certificate",
            field_path="certificate_no",
            message="El número de certificado de molino no fue identificado en el documento.",
        ))

    supplier = document_metadata.get("supplier") or document_metadata.get("manufacturer")
    if not supplier or str(supplier).strip() == "":
        issues.append(QualityIssue(
            code="missing_supplier",
            category=QualityCategory.MISSING,
            severity=QualitySeverity.WARNING,
            scope="certificate",
            field_path="supplier",
            message="El fabricante o proveedor del acta no fue identificado con certeza.",
        ))

    standard = document_metadata.get("standard")
    if not standard or str(standard).strip() == "":
        issues.append(QualityIssue(
            code="missing_standard",
            category=QualityCategory.MISSING,
            severity=QualitySeverity.WARNING,
            scope="certificate",
            field_path="standard",
            message="La norma o especificación técnica no fue identificada en el encabezado del acta.",
        ))

    # 2. Heats evaluation & duplicate heats conflict detection
    heats_by_number: dict[str, list[dict[str, Any]]] = {}
    for heat in heats:
        h_no = str(heat.get("heat_no") or "").strip()
        if h_no:
            heats_by_number.setdefault(h_no, []).append(heat)

    for h_no, duplicates in heats_by_number.items():
        if len(duplicates) > 1:
            # Check if duplicates contain contradictory standards or grades
            standards = {d.get("standard") for d in duplicates if d.get("standard")}
            grades = {d.get("grade") for d in duplicates if d.get("grade")}
            if len(standards) > 1 or len(grades) > 1:
                issues.append(QualityIssue(
                    code="duplicate_heat_conflict",
                    category=QualityCategory.CONTRADICTION,
                    severity=QualitySeverity.BLOCKING,
                    scope="heat",
                    entity_identifier=h_no,
                    field_path="heat_no",
                    message=f"La colada {h_no} aparece duplicada con normas o grados contradictorios.",
                    raw_value=h_no,
                ))

    # 3. Product-level required fields & family detection
    family = ProductFamily.FLAT_ROLLED_GENERAL
    if products:
        family = detect_product_family(products[0])

    if not products:
        issues.append(QualityIssue(
            code="no_products_extracted",
            category=QualityCategory.MISSING,
            severity=QualitySeverity.BLOCKING,
            scope="certificate",
            field_path="products",
            message="El documento no contiene productos o rollos extraídos.",
        ))

    known_heat_ids = {h.get("id") for h in heats if h.get("id") is not None}
    known_heat_nos = {str(h.get("heat_no") or "").strip() for h in heats}

    for prod in products:
        prod_id = str(prod.get("product_identifier") or prod.get("product_id") or "").strip()
        prod_family = detect_product_family(prod)
        prod_heat_id = prod.get("heat_id")
        prod_heat_no = str(prod.get("heat_no") or "").strip()

        # Scope validation: product must reference an existing heat
        if prod_heat_id is not None and prod_heat_id not in known_heat_ids:
            issues.append(QualityIssue(
                code="orphaned_product",
                category=QualityCategory.CONTRADICTION,
                severity=QualitySeverity.BLOCKING,
                scope="product",
                entity_identifier=prod_id,
                field_path="heat_id",
                message=f"El producto {prod_id} referencia una colada inexistente (ID: {prod_heat_id}).",
                raw_value=prod_heat_id,
            ))
        elif not prod_heat_id and prod_heat_no and prod_heat_no not in known_heat_nos:
            issues.append(QualityIssue(
                code="orphaned_product",
                category=QualityCategory.CONTRADICTION,
                severity=QualitySeverity.BLOCKING,
                scope="product",
                entity_identifier=prod_id,
                field_path="heat_no",
                message=f"El producto {prod_id} referencia una colada no registrada ({prod_heat_no}).",
                raw_value=prod_heat_no,
            ))

        # Required fields by family
        thickness = prod.get("thickness_mm")
        if thickness is None:
            issues.append(QualityIssue(
                code="missing_required_field",
                category=QualityCategory.MISSING,
                severity=QualitySeverity.BLOCKING,
                scope="product",
                entity_identifier=prod_id,
                field_path="thickness_mm",
                message=f"El producto {prod_id} carece de espesor nominal (campo obligatorio para laminados).",
            ))
        else:
            try:
                th_dec = Decimal(str(thickness))
                if th_dec <= 0:
                    issues.append(QualityIssue(
                        code="impossible_dimension",
                        category=QualityCategory.CONTRADICTION,
                        severity=QualitySeverity.BLOCKING,
                        scope="product",
                        entity_identifier=prod_id,
                        field_path="thickness_mm",
                        message=f"El espesor del producto {prod_id} debe ser mayor a 0 ({th_dec} mm).",
                        raw_value=thickness,
                        normalized_value=th_dec,
                    ))
            except Exception:
                issues.append(QualityIssue(
                    code="invalid_dimension_format",
                    category=QualityCategory.CONTRADICTION,
                    severity=QualitySeverity.BLOCKING,
                    scope="product",
                    entity_identifier=prod_id,
                    field_path="thickness_mm",
                    message=f"El espesor del producto {prod_id} no tiene un valor numérico válido.",
                    raw_value=thickness,
                ))

        width = prod.get("width_mm")
        if width is None:
            issues.append(QualityIssue(
                code="missing_required_field",
                category=QualityCategory.MISSING,
                severity=QualitySeverity.BLOCKING,
                scope="product",
                entity_identifier=prod_id,
                field_path="width_mm",
                message=f"El producto {prod_id} carece de ancho nominal (campo obligatorio para clasificación).",
            ))
        else:
            try:
                w_dec = Decimal(str(width))
                if w_dec <= 0:
                    issues.append(QualityIssue(
                        code="impossible_dimension",
                        category=QualityCategory.CONTRADICTION,
                        severity=QualitySeverity.BLOCKING,
                        scope="product",
                        entity_identifier=prod_id,
                        field_path="width_mm",
                        message=f"El ancho del producto {prod_id} debe ser mayor a 0 ({w_dec} mm).",
                        raw_value=width,
                        normalized_value=w_dec,
                    ))
            except Exception:
                issues.append(QualityIssue(
                    code="invalid_dimension_format",
                    category=QualityCategory.CONTRADICTION,
                    severity=QualitySeverity.BLOCKING,
                    scope="product",
                    entity_identifier=prod_id,
                    field_path="width_mm",
                    message=f"El ancho del producto {prod_id} no tiene un valor numérico válido.",
                    raw_value=width,
                ))

        if prod_family == ProductFamily.FLAT_ROLLED_PLATE:
            length = prod.get("length_m")
            if length is None:
                issues.append(QualityIssue(
                    code="missing_plate_length",
                    category=QualityCategory.MISSING,
                    severity=QualitySeverity.WARNING,
                    scope="product",
                    entity_identifier=prod_id,
                    field_path="length_m",
                    message=f"La plancha {prod_id} no especifica longitud (largo en metros).",
                ))
            else:
                try:
                    l_dec = Decimal(str(length))
                    if l_dec <= 0:
                        issues.append(QualityIssue(
                            code="impossible_dimension",
                            category=QualityCategory.CONTRADICTION,
                            severity=QualitySeverity.BLOCKING,
                            scope="product",
                            entity_identifier=prod_id,
                            field_path="length_m",
                            message=f"La longitud de la plancha {prod_id} debe ser mayor a 0 ({l_dec} m).",
                            raw_value=length,
                            normalized_value=l_dec,
                        ))
                except Exception:
                    issues.append(QualityIssue(
                        code="invalid_dimension_format",
                        category=QualityCategory.CONTRADICTION,
                        severity=QualitySeverity.BLOCKING,
                        scope="product",
                        entity_identifier=prod_id,
                        field_path="length_m",
                        message=f"La longitud del producto {prod_id} no tiene un valor numérico válido.",
                        raw_value=length,
                    ))

        # Weight sanity check
        weight = prod.get("weight_kg")
        if weight is not None:
            try:
                wt_dec = Decimal(str(weight))
                if wt_dec <= 0:
                    issues.append(QualityIssue(
                        code="impossible_dimension",
                        category=QualityCategory.CONTRADICTION,
                        severity=QualitySeverity.BLOCKING,
                        scope="product",
                        entity_identifier=prod_id,
                        field_path="weight_kg",
                        message=f"El peso del producto {prod_id} debe ser mayor a 0 ({wt_dec} kg).",
                        raw_value=weight,
                        normalized_value=wt_dec,
                    ))
            except Exception:
                issues.append(QualityIssue(
                    code="invalid_dimension_format",
                    category=QualityCategory.CONTRADICTION,
                    severity=QualitySeverity.BLOCKING,
                    scope="product",
                    entity_identifier=prod_id,
                    field_path="weight_kg",
                    message=f"El peso del producto {prod_id} no tiene un valor numérico válido.",
                    raw_value=weight,
                ))

    # 4. Chemical composition sanity: bounds, impossible sums, scopes
    total_percentages_by_scope: dict[tuple[str, int | None], Decimal] = {}
    elements_by_scope: dict[tuple[str, int | None], set[str]] = {}

    for comp in compositions:
        elem = str(comp.get("element") or "").strip()
        val = comp.get("percentage")
        raw_val = comp.get("raw_value") or comp.get("raw_value_json")
        p_id = comp.get("product_id")
        h_id = comp.get("heat_id")
        scope_key = ("product", p_id) if p_id is not None else ("heat", h_id)

        if not elem:
            continue

        elements_by_scope.setdefault(scope_key, set()).add(elem)

        if val is not None:
            try:
                dec_val = Decimal(str(val))
                if dec_val < Decimal("0") or dec_val > Decimal("100"):
                    issues.append(QualityIssue(
                        code="chemical_percentage_out_of_range",
                        category=QualityCategory.CONTRADICTION,
                        severity=QualitySeverity.BLOCKING,
                        scope=scope_key[0],
                        entity_identifier=str(scope_key[1]),
                        field_path=f"composition_pct.{elem}",
                        message=f"El porcentaje de {elem} ({dec_val} %) está fuera del rango físico [0, 100].",
                        raw_value=raw_val,
                        normalized_value=dec_val,
                    ))
                else:
                    total_percentages_by_scope[scope_key] = (
                        total_percentages_by_scope.get(scope_key, Decimal("0")) + dec_val
                    )
            except Exception:
                issues.append(QualityIssue(
                    code="invalid_chemical_format",
                    category=QualityCategory.CONTRADICTION,
                    severity=QualitySeverity.BLOCKING,
                    scope=scope_key[0],
                    entity_identifier=str(scope_key[1]),
                    field_path=f"composition_pct.{elem}",
                    message=f"El valor químico de {elem} no es numérico válido.",
                    raw_value=raw_val,
                ))

    # Check sum of chemical elements <= 100.0%
    for scope_key, sum_pct in total_percentages_by_scope.items():
        if sum_pct > Decimal("100.0"):
            issues.append(QualityIssue(
                code="chemical_sum_exceeds_100",
                category=QualityCategory.CONTRADICTION,
                severity=QualitySeverity.BLOCKING,
                scope=scope_key[0],
                entity_identifier=str(scope_key[1]),
                field_path="composition_pct",
                message=f"La suma total de elementos químicos en {scope_key[0]} {scope_key[1]} ({sum_pct} %) excede el 100 %.",
                normalized_value=sum_pct,
            ))

    # Check if products have associated chemistry (either direct or via heat)
    for prod in products:
        p_id = prod.get("id") or prod.get("product_identifier")
        h_id = prod.get("heat_id")
        has_prod_chem = bool(elements_by_scope.get(("product", p_id)))
        has_heat_chem = bool(elements_by_scope.get(("heat", h_id)))
        if not has_prod_chem and not has_heat_chem:
            issues.append(QualityIssue(
                code="missing_required_chemistry",
                category=QualityCategory.MISSING,
                severity=QualitySeverity.BLOCKING,
                scope="product",
                entity_identifier=str(p_id),
                field_path="composition_pct",
                message=f"El producto {p_id} no cuenta con análisis químico ni propio ni de su colada.",
            ))

    # 5. Observation-level confidence, provenance, and unit coherence
    for obs in observations:
        f_path = str(obs.get("field_path") or "").strip()
        conf = obs.get("confidence")
        src_text = str(obs.get("source_text") or "").lower()
        unit = obs.get("unit")
        inherited = bool(obs.get("inherited"))

        # Provenance classification
        if "captura_manual" in src_text or "correccion" in src_text:
            provenance_counts["manual_capture"] += 1
        elif inherited:
            provenance_counts["inherited"] += 1
        elif "ocr" in src_text:
            provenance_counts["ocr_text"] += 1
        elif conf is not None and conf >= 0.90:
            provenance_counts["digital_text"] += 1
        else:
            provenance_counts["unknown"] += 1

        # Confidence check
        if conf is not None and conf < CONFIDENCE_THRESHOLD_MIN:
            is_critical = f_path in {"thickness_mm", "width_mm"} or f_path.startswith("composition_pct.")
            issues.append(QualityIssue(
                code="low_confidence_field",
                category=QualityCategory.LOW_CONFIDENCE,
                severity=QualitySeverity.BLOCKING if is_critical else QualitySeverity.WARNING,
                scope="product" if obs.get("product_id") else "heat" if obs.get("heat_id") else "certificate",
                entity_identifier=str(obs.get("product_id") or obs.get("heat_id") or ""),
                field_path=f_path,
                message=f"La observación del campo '{f_path}' tiene baja confianza de extracción ({conf:.2f}).",
                raw_value=obs.get("raw_value") or obs.get("raw_value_json"),
                normalized_value=obs.get("normalized_value") or obs.get("normalized_value_json"),
                confidence=conf,
                page_number=obs.get("page_number"),
                bbox=obs.get("bbox") or obs.get("bbox_json"),
            ))

        # Incoherent unit detection
        if unit:
            u_clean = unit.strip().lower()
            if f_path in {"thickness_mm", "width_mm"} and u_clean not in {"mm", "milimetros"}:
                issues.append(QualityIssue(
                    code="incoherent_unit",
                    category=QualityCategory.CONTRADICTION,
                    severity=QualitySeverity.BLOCKING,
                    scope="product",
                    entity_identifier=str(obs.get("product_id") or ""),
                    field_path=f_path,
                    message=f"Unidad incoherente '{unit}' para la dimensión {f_path} (se espera 'mm').",
                    raw_value=unit,
                ))
            elif f_path.startswith("composition_pct.") and u_clean not in VALID_CHEMISTRY_UNITS:
                issues.append(QualityIssue(
                    code="incoherent_unit",
                    category=QualityCategory.CONTRADICTION,
                    severity=QualitySeverity.BLOCKING,
                    scope="chemistry",
                    field_path=f_path,
                    message=f"Unidad incoherente '{unit}' para composición química (se espera '%').",
                    raw_value=unit,
                ))

    blocking_count = sum(1 for issue in issues if issue.severity == QualitySeverity.BLOCKING)
    warning_count = sum(1 for issue in issues if issue.severity == QualitySeverity.WARNING)

    # Calculate overall quality score: penalized by blocking (0.25 each) and warnings (0.05 each)
    base_score = 1.0
    deductions = (blocking_count * 0.25) + (warning_count * 0.05)
    quality_score = max(0.0, min(1.0, base_score - deductions))

    status = "clean" if blocking_count == 0 else "needs_review"

    return DocumentQualityReport(
        certificate_id=certificate_id,
        status=status,
        quality_score=quality_score,
        product_family=family,
        issues=tuple(issues),
        provenance_summary=provenance_counts,
        blocking_count=blocking_count,
        warning_count=warning_count,
    )
