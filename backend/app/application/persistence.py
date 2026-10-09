"""Persist the existing canonical certificate contract without changing it."""

from __future__ import annotations

from datetime import datetime
import re
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.config import Settings
from backend.app.infrastructure.database.models import (
    ChemicalComposition,
    Document,
    Heat,
    Manufacturer,
    MillCertificate,
    Observation,
    Product,
)


def normalize_manufacturer_name(value: str) -> str:
    return " ".join(value.casefold().split())


def parse_certificate_date(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    text = str(value).strip()
    if re.search(r"\b(?:about|approx|circa)\b", text, re.I):
        return None
    months = {name: f"{index:02}" for index, name in enumerate(
        ("JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"), 1)}
    match = re.fullmatch(r"([A-Za-z]{3})\.?\s+(\d{1,2}),?\s+(\d{4})", text)
    if match and match[1].upper() in months:
        text = f"{match[3]}-{months[match[1].upper()]}-{int(match[2]):02}"
    for pattern in ("%Y%m%d", "%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(text, pattern)
        except ValueError:
            continue
    return None


class CertificatePersistenceService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def persist_normalized(
        self,
        session: Session,
        *,
        document_id: int,
        normalized: dict[str, Any],
    ) -> MillCertificate:
        certificate = session.scalar(
            select(MillCertificate).where(MillCertificate.document_id == document_id)
        )
        if certificate is None:
            raise ValueError(f"Document {document_id} has no certificate placeholder")
        if session.scalar(select(func.count(Product.id)).where(Product.certificate_id == certificate.id)):
            return certificate

        document_data = normalized.get("document") or {}
        supplier = str(document_data.get("supplier") or "").strip()
        if supplier:
            normalized_name = normalize_manufacturer_name(supplier)
            manufacturer = session.scalar(
                select(Manufacturer).where(Manufacturer.normalized_name == normalized_name)
            )
            if manufacturer is None:
                manufacturer = Manufacturer(name=supplier, normalized_name=normalized_name)
                session.add(manufacturer)
                session.flush()
            certificate.manufacturer_id = manufacturer.id

        certificate_no = str(document_data.get("certificate_no") or "").strip() or None
        certificate.certificate_no = certificate_no
        parsed_date = parse_certificate_date(
            document_data.get("certificate_date_raw") or document_data.get("issue_date_raw")
        )
        certificate.certificate_date = parsed_date.date() if parsed_date else None
        products_data = normalized.get("products") or []
        certificate.standard = normalized.get("standard") or next(
            (item.get("standard") for item in products_data if item.get("standard")), None
        )
        certificate.product_name = document_data.get("product_name")

        if certificate.manufacturer_id and certificate_no:
            previous = session.scalar(
                select(MillCertificate)
                .where(
                    MillCertificate.manufacturer_id == certificate.manufacturer_id,
                    MillCertificate.certificate_no == certificate_no,
                    MillCertificate.id != certificate.id,
                )
                .order_by(MillCertificate.revision_number.desc())
                .limit(1)
            )
            if previous:
                certificate.previous_revision_id = previous.id
                certificate.revision_number = previous.revision_number + 1

        products_by_heat: dict[str, list[tuple[Product, dict[str, Any]]]] = {}
        heats: dict[str, Heat] = {}
        for product_data in products_data:
            heat_no = str(product_data.get("heat_no") or "UNKNOWN").strip()
            heat = heats.get(heat_no)
            if heat is None:
                heat = Heat(
                    certificate_id=certificate.id,
                    heat_no=heat_no,
                    grade=product_data.get("grade"),
                    standard=product_data.get("standard") or certificate.standard,
                    properties_json={},
                )
                session.add(heat)
                session.flush()
                heats[heat_no] = heat
            product = Product(
                certificate_id=certificate.id,
                heat_id=heat.id,
                product_identifier=str(product_data["product_id"]),
                label_no=product_data.get("label_no"),
                product_type=certificate.product_name,
                form=product_data.get("form"),
                coiled=product_data.get("coiled"),
                rolling=product_data.get("rolling"),
                width_mm=self._decimal(product_data.get("width_mm")),
                thickness_mm=self._decimal(product_data.get("thickness_mm")),
                length_m=self._decimal(product_data.get("length_m")),
                weight_kg=self._decimal(product_data.get("weight_kg")),
                net_weight_kg=self._decimal(product_data.get("net_weight_kg")),
                gross_weight_kg=self._decimal(product_data.get("gross_weight_kg")),
                properties_json={
                    "condition": product_data.get("condition"),
                    "coating": product_data.get("coating"),
                    "mechanical_properties": product_data.get("mechanical_properties"),
                    "edge_condition": product_data.get("edge_condition"),
                },
            )
            session.add(product)
            session.flush()
            products_by_heat.setdefault(heat_no, []).append((product, product_data))
            self._persist_observations(session, certificate.id, heat.id, product, product_data)

        for heat_no, entries in products_by_heat.items():
            compositions = [entry[1].get("composition_pct") or {} for entry in entries]
            shared = heat_no != "UNKNOWN" and bool(compositions) and all(value == compositions[0] for value in compositions[1:])
            # Spreadsheet cells belong to individual rows even when percentages match.
            if any(item[1].get("source_format") == "xlsx" for item in entries):
                shared = False
            # Keep each roll's verification and citations, even when percentages match.
            if any(detail.get("verification") for _, data in entries
                   for detail in (data.get("observations", {}).get("composition_pct") or {}).values()):
                shared = False
            if shared:
                self._persist_composition(
                    session, certificate_id=certificate.id,
                    heat_id=heats[heat_no].id, product_id=None,
                    composition=compositions[0], observations=entries[0][1],
                )
            else:
                for product, product_data in entries:
                    self._persist_composition(
                        session, certificate_id=certificate.id,
                        heat_id=None, product_id=product.id,
                        composition=product_data.get("composition_pct") or {},
                        observations=product_data,
                    )

        document = session.get(Document, document_id)
        if document:
            document.processing_status = "succeeded"
        session.flush()
        return certificate

    @staticmethod
    def _decimal(value: Any) -> Decimal | None:
        return None if value is None else Decimal(str(value))

    def _persist_observations(
        self,
        session: Session,
        certificate_id: int,
        heat_id: int,
        product: Product,
        product_data: dict[str, Any],
    ) -> None:
        observations = product_data.get("observations") or {}
        for field_path, detail in observations.items():
            if field_path == "composition_pct" or not isinstance(detail, dict):
                continue
            session.add(
                Observation(
                    certificate_id=certificate_id,
                    heat_id=heat_id,
                    product_id=product.id,
                    field_path=field_path,
                    raw_value_json=detail.get("raw_value"),
                    normalized_value_json=detail.get("normalized_value"),
                    verification_json=detail.get("verification"),
                    unit=detail.get("unit"),
                    confidence=detail.get("confidence", 1.0),
                    page_number=detail.get("page_number", detail.get("page")),
                    bbox_json=detail.get("bbox"),
                    source_text=detail.get("source_text", detail.get("region")),
                    inherited=bool(detail.get("inherited")),
                )
            )
        for evidence in product_data.get("evidence") or []:
            session.add(
                Observation(
                    certificate_id=certificate_id,
                    heat_id=heat_id,
                    product_id=product.id,
                    field_path="evidence",
                    raw_value_json=evidence,
                    normalized_value_json=None,
                    page_number=evidence.get("page") if isinstance(evidence, dict) else None,
                    source_text=evidence.get("region") if isinstance(evidence, dict) else None,
                    confidence=1.0,
                )
            )
        for field_path, normalized_value, unit in self._additional_product_observations(product_data):
            if field_path in observations:
                continue
            session.add(
                Observation(
                    certificate_id=certificate_id,
                    heat_id=heat_id,
                    product_id=product.id,
                    field_path=field_path,
                    raw_value_json=normalized_value,
                    normalized_value_json=normalized_value,
                    unit=unit,
                    confidence=1.0,
                )
            )

    @staticmethod
    def _additional_product_observations(
        product_data: dict[str, Any],
    ) -> list[tuple[str, Any, str | None]]:
        observations: list[tuple[str, Any, str | None]] = [
            ("form", product_data.get("form"), None),
            ("coiled", product_data.get("coiled"), None),
            ("rolling", product_data.get("rolling"), None),
        ]
        for key, value in (product_data.get("mechanical_properties") or {}).items():
            unit = "MPa" if key in {"yield_strength_mpa", "tensile_strength_mpa"} else None
            observations.append((f"mechanical_properties.{key}", value, unit))
        for key, value in (product_data.get("coating") or {}).items():
            unit = "g/m²" if key in {"superior_g_m2", "inferior_g_m2"} else None
            observations.append((f"coating.{key}", value, unit))
        return [item for item in observations if item[1] is not None]

    def _persist_composition(
        self,
        session: Session,
        *,
        certificate_id: int,
        heat_id: int | None,
        product_id: int | None,
        composition: dict[str, Any],
        observations: dict[str, Any],
    ) -> None:
        details = ((observations.get("observations") or {}).get("composition_pct") or {})
        for element, percentage in composition.items():
            detail = details.get(element) or {}
            session.add(
                ChemicalComposition(
                    heat_id=heat_id,
                    product_id=product_id,
                    element=element,
                    raw_value_json=detail.get("raw_value"),
                    percentage=self._decimal(percentage),
                    inherited=bool(detail.get("inherited")),
                    source_label=detail.get("source_label"),
                )
            )
            session.add(
                Observation(
                    certificate_id=certificate_id,
                    heat_id=heat_id,
                    product_id=product_id,
                    field_path=f"composition_pct.{element}",
                    raw_value_json=detail.get("raw_value"),
                    normalized_value_json=percentage,
                    verification_json=detail.get("verification"),
                    unit="%",
                    confidence=detail.get("confidence", 1.0),
                    page_number=detail.get("page_number", detail.get("page")),
                    bbox_json=detail.get("bbox"),
                    source_text=detail.get("source_text", detail.get("region")),
                    inherited=bool(detail.get("inherited")),
                )
            )
