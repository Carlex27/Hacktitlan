"""Auditable Excel exports generated entirely by the backend."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.table import Table, TableStyleInfo
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from backend.app.config import Settings
from backend.app.infrastructure.database.models import (
    ClassificationResult,
    ClassificationRun,
    Correction,
    Heat,
    Manufacturer,
    MillCertificate,
    Observation,
    Product,
    RuleSet,
)
from backend.app.infrastructure.database.models.core import ChemicalComposition


class ExcelExportService:
    sheet_names = [
        "Resumen", "Actas", "Coladas", "Rollos", "Composición",
        "Clasificación", "Evidencia", "Auditoría",
    ]

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def export_certificates(
        self,
        session: Session,
        *,
        certificate_ids: list[int],
        heat_ids: list[int] | None = None,
        classification_run_ids: list[int] | None = None,
        destination: Path,
        official: bool,
    ) -> Path:
        if not certificate_ids:
            raise ValueError("Debe seleccionar al menos un acta")
        certificate_ids = list(dict.fromkeys(certificate_ids))
        requested_heat_ids = list(dict.fromkeys(heat_ids or []))
        certificates = session.scalars(
            select(MillCertificate).where(MillCertificate.id.in_(certificate_ids)).order_by(MillCertificate.id)
        ).all()
        if len(certificates) != len(set(certificate_ids)):
            raise ValueError("Una o más actas no existen")
        restrict_heats = bool(requested_heat_ids)
        heats_query = select(Heat).where(Heat.certificate_id.in_(certificate_ids))
        if restrict_heats:
            heats_query = heats_query.where(Heat.id.in_(requested_heat_ids))
        heats = session.scalars(heats_query.order_by(Heat.id)).all()
        if restrict_heats and len(heats) != len(requested_heat_ids):
            raise ValueError("Una o más coladas no pertenecen al alcance seleccionado")
        selected_heat_ids = [item.id for item in heats]
        products_query = select(Product).where(Product.certificate_id.in_(certificate_ids))
        if restrict_heats:
            products_query = products_query.where(Product.heat_id.in_(selected_heat_ids))
        products = session.scalars(products_query.order_by(Product.id)).all()
        product_ids = [item.id for item in products]
        observation_query = select(Observation).where(Observation.certificate_id.in_(certificate_ids))
        if restrict_heats:
            observation_query = observation_query.where(
                or_(Observation.heat_id.in_(selected_heat_ids), Observation.product_id.in_(product_ids))
            )
        observations = session.scalars(observation_query.order_by(Observation.id)).all()
        chemistry = []
        if selected_heat_ids or product_ids:
            chemistry = session.scalars(
                select(ChemicalComposition)
                .where(or_(ChemicalComposition.heat_id.in_(selected_heat_ids), ChemicalComposition.product_id.in_(product_ids)))
                .order_by(ChemicalComposition.id)
            ).all()
        runs_query = select(ClassificationRun).where(
            ClassificationRun.certificate_id.in_(certificate_ids)
        )
        if classification_run_ids:
            requested_run_ids = list(dict.fromkeys(classification_run_ids))
            runs_query = runs_query.where(ClassificationRun.id.in_(requested_run_ids))
            runs = session.scalars(runs_query.order_by(ClassificationRun.id)).all()
            if len(runs) != len(requested_run_ids):
                raise ValueError("Una ejecución no pertenece al alcance seleccionado")
            if official and any(run.approval_status != "approved" for run in runs):
                raise ValueError("Un reporte oficial sólo admite ejecuciones aprobadas")
        else:
            if official:
                runs_query = runs_query.where(ClassificationRun.approval_status == "approved")
            available_runs = session.scalars(
                runs_query.order_by(ClassificationRun.certificate_id, ClassificationRun.id.desc())
            ).all()
            latest_by_certificate: dict[int, ClassificationRun] = {}
            for run in available_runs:
                latest_by_certificate.setdefault(run.certificate_id, run)
            runs = list(latest_by_certificate.values())
        run_ids = [item.id for item in runs]
        results = session.scalars(
            select(ClassificationResult).where(ClassificationResult.classification_run_id.in_(run_ids)).order_by(ClassificationResult.id)
        ).all() if run_ids else []
        makers = {item.id: item for item in session.scalars(select(Manufacturer)).all()}
        rules = {item.id: item for item in session.scalars(select(RuleSet)).all()}
        corrections = session.scalars(
            select(Correction).where(Correction.certificate_id.in_(certificate_ids)).order_by(Correction.id)
        ).all()

        workbook = Workbook()
        workbook.remove(workbook.active)
        for name in self.sheet_names:
            workbook.create_sheet(name)
        notice = self.settings.demo_notice if official else f"PRELIMINAR — {self.settings.demo_notice}"
        summary_rows = [
            ["Aviso", notice],
            ["Generado UTC", datetime.now(timezone.utc).isoformat()],
            ["Tipo", "Oficial (sólo aprobados)" if official else "Preliminar"],
            ["Actas", len(certificates)], ["Coladas", len(heats)], ["Rollos", len(products)],
            ["Ejecuciones de clasificación", ", ".join(str(run.id) for run in runs) or "Ninguna"],
        ] + [[f"Hoja {name}", f"Ir a {name}"] for name in self.sheet_names if name != "Resumen"]
        self._write_sheet(workbook["Resumen"], ["Campo", "Valor"], summary_rows, "ResumenTable", notice)
        for row in range(4, workbook["Resumen"].max_row + 1):
            label = workbook["Resumen"].cell(row, 1).value
            if isinstance(label, str) and label.startswith("Hoja "):
                target = label.removeprefix("Hoja ")
                link = workbook["Resumen"].cell(row, 2)
                link.hyperlink = f"#'{target}'!A1"
                link.style = "Hyperlink"
        self._write_sheet(workbook["Actas"],
            ["certificate_id", "document_id", "número", "fabricante", "fecha_acta", "fecha_carga", "estado", "revisión"],
            [[c.id, c.document_id, c.certificate_no, makers.get(c.manufacturer_id).name if c.manufacturer_id in makers else None,
              c.certificate_date, c.uploaded_at, c.approval_status, c.revision_number] for c in certificates],
            "ActasTable", notice)
        self._write_sheet(workbook["Coladas"],
            ["heat_id", "certificate_id", "colada", "norma", "grado", "propiedades"],
            [[h.id, h.certificate_id, h.heat_no, h.standard, h.grade, str(h.properties_json)] for h in heats],
            "ColadasTable", notice)
        self._write_sheet(workbook["Rollos"],
            ["product_id", "certificate_id", "heat_id", "identificador", "etiqueta", "tipo", "forma", "enrollado", "laminado", "ancho_mm", "espesor_mm", "peso_kg"],
            [[p.id, p.certificate_id, p.heat_id, p.product_identifier, p.label_no, p.product_type, p.form,
              p.coiled, p.rolling, p.width_mm, p.thickness_mm, p.weight_kg] for p in products],
            "RollosTable", notice)
        self._write_sheet(workbook["Composición"],
            ["composition_id", "heat_id", "product_id", "elemento", "valor_original", "porcentaje", "heredado", "etiqueta_fuente"],
            [[c.id, c.heat_id, c.product_id, c.element, str(c.raw_value_json) if c.raw_value_json is not None else None,
              c.percentage, c.inherited, c.source_label] for c in chemistry],
            "ComposicionTable", notice)
        run_by_id = {run.id: run for run in runs}
        self._write_sheet(workbook["Clasificación"],
            ["result_id", "classification_run_id", "product_id", "tipo", "fracción", "NICO", "descripción", "resultado", "faltantes", "candidatos", "estado", "reglas"],
            [[r.id, r.classification_run_id, r.product_id, r.product_type, r.fraction, r.nico, r.description, r.outcome,
              ", ".join(r.details_json.get("missing_fields") or []),
              ", ".join(r.details_json.get("candidates") or []),
              run_by_id[r.classification_run_id].approval_status,
              rules.get(run_by_id[r.classification_run_id].rule_set_id).version if run_by_id[r.classification_run_id].rule_set_id in rules else None]
             for r in results], "ClasificacionTable", notice)
        self._write_sheet(workbook["Evidencia"],
            ["observation_id", "certificate_id", "heat_id", "product_id", "campo", "original", "normalizado", "unidad", "confianza", "página", "coordenadas", "texto_fuente", "vigente"],
            [[o.id, o.certificate_id, o.heat_id, o.product_id, o.field_path, str(o.raw_value_json) if o.raw_value_json is not None else None,
              str(o.normalized_value_json) if o.normalized_value_json is not None else None, o.unit, o.confidence,
              o.page_number, str(o.bbox_json) if o.bbox_json else None, o.source_text, o.is_current] for o in observations],
            "EvidenciaTable", notice)
        self._write_sheet(workbook["Auditoría"],
            ["correction_id", "certificate_id", "observación_anterior", "observación_nueva", "persona", "motivo", "equipo", "fecha"],
            [[c.id, c.certificate_id, c.previous_observation_id, c.replacement_observation_id,
              c.person_name, c.reason, c.workstation_name, c.created_at] for c in corrections],
            "AuditoriaTable", notice)
        destination.parent.mkdir(parents=True, exist_ok=True)
        workbook.save(destination)
        self._validate(destination, len(certificates), len(heats), len(products))
        return destination

    @staticmethod
    def _write_sheet(sheet, headers: list[str], rows: Iterable[list[Any]], table_name: str, notice: str) -> None:
        sheet["A1"] = notice
        sheet["A1"].font = Font(bold=True, color="9C0006")
        sheet.append([])
        sheet.append(headers)
        for row in rows:
            sheet.append(row)
        for cell in sheet[3]:
            cell.fill = PatternFill("solid", fgColor="1F4E78")
            cell.font = Font(color="FFFFFF", bold=True)
            cell.alignment = Alignment(horizontal="center")
        sheet.freeze_panes = "A4"
        sheet.auto_filter.ref = f"A3:{sheet.cell(3, len(headers)).coordinate}"
        if sheet.max_row >= 4:
            table = Table(displayName=table_name, ref=f"A3:{sheet.cell(sheet.max_row, len(headers)).coordinate}")
            table.tableStyleInfo = TableStyleInfo(name="TableStyleMedium2", showRowStripes=True)
            sheet.add_table(table)
        for column in sheet.columns:
            width = min(max(len(str(cell.value or "")) for cell in column) + 2, 45)
            sheet.column_dimensions[column[0].column_letter].width = max(width, 12)

    @staticmethod
    def _validate(path: Path, certificates: int, heats: int, products: int) -> None:
        workbook = load_workbook(path, read_only=True, data_only=False)
        try:
            if len(list(workbook["Actas"].iter_rows(min_row=4, values_only=True))) != certificates:
                raise RuntimeError("El conteo de actas exportadas no coincide")
            if len(list(workbook["Coladas"].iter_rows(min_row=4, values_only=True))) != heats:
                raise RuntimeError("El conteo de coladas exportadas no coincide")
            if len(list(workbook["Rollos"].iter_rows(min_row=4, values_only=True))) != products:
                raise RuntimeError("El conteo de rollos exportados no coincide")
        finally:
            workbook.close()
