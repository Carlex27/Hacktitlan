"""Typed draft templates and conservative previews using the common normalizer."""
from __future__ import annotations

from hashlib import sha256
from decimal import Decimal
import json
from pathlib import Path
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator

from backend.app.certificate_parser.measurement_units import dimension_unit, dimension_value
from backend.app.certificate_parser.mill_certificate import ELEMENT_ALIASES, normalize_certificate
from backend.app.certificate_parser.regions import PageRegion, select_region
from backend.app.domain.document import DocumentLayout, PageSource

Target = Literal["certificate_no", "supplier", "standard", "product_id", "heat_no",
                 "thickness_mm", "width_mm", "length_raw", "weight_kg",
                 "yield_strength_mpa", "tensile_strength_mpa", "elongation_pct", "chemistry"]
METADATA_FIELDS = {"certificate_no", "supplier", "standard"}


class TemplateModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, strict=True)


class ValueMapping(TemplateModel):
    target: Target
    element: str | None = Field(default=None, pattern=r"^[A-Z][a-z]?(?:_total|_soluble)?$", max_length=20)
    unit: Literal["mm", "cm", "in", "ft", "m", "kg", "MPa", "%"] | None = None
    exponent: int | None = Field(default=None, ge=-6, le=6, strict=True)
    required: bool = True
    decimal_separator: Literal[".", ","] = "."

    @property
    def key(self) -> str:
        return f"chemistry.{self.element}" if self.target == "chemistry" else self.target

    @model_validator(mode="after")
    def compatible_units(self) -> "ValueMapping":
        units = {
            "thickness_mm": {"mm", "cm", "in", "ft", "m"},
            "width_mm": {"mm", "cm", "in", "ft", "m"},
            "length_raw": {"mm", "cm", "in", "ft", "m"},
            "weight_kg": {"kg"}, "yield_strength_mpa": {"MPa"},
            "tensile_strength_mpa": {"MPa"}, "elongation_pct": {"%"}, "chemistry": {"%"},
        }
        if self.target in units and self.unit not in units[self.target]:
            raise ValueError("La unidad debe ser explícita y compatible con el campo")
        if self.target not in units and self.unit is not None:
            raise ValueError("Este identificador no admite unidad")
        if self.target == "chemistry":
            if self.element is None or self.exponent is None:
                raise ValueError("La química requiere elemento y exponente explícitos")
            self.element = ELEMENT_ALIASES.get(self.element.casefold(), self.element)
        elif self.element is not None or self.exponent is not None:
            raise ValueError("Elemento y exponente sólo se permiten en química")
        return self


class FieldMapping(ValueMapping):
    page_number: int = Field(ge=1, strict=True)
    region: PageRegion


class ColumnMapping(ValueMapping):
    header: str = Field(min_length=1, max_length=200)


class TableMapping(TemplateModel):
    page_number: int = Field(ge=1, strict=True)
    region: PageRegion
    role: Literal["products", "chemistry", "mechanical"] = "products"
    join_key: Literal["product_id", "heat_no"] = "product_id"
    header_row: int = Field(default=0, ge=0, le=100, strict=True)
    columns: list[ColumnMapping] = Field(min_length=1, max_length=150)

    @model_validator(mode="after")
    def unique_columns(self) -> "TableMapping":
        keys = [column.key for column in self.columns]
        headers = [column.header.strip().casefold() for column in self.columns]
        if len(set(keys)) != len(keys) or len(set(headers)) != len(headers) or not all(headers):
            raise ValueError("Columnas duplicadas o encabezados vacíos")
        if any(column.target in METADATA_FIELDS for column in self.columns):
            raise ValueError("Los metadatos se asignan como campos, no columnas")
        if self.role == "products":
            if "product_id" not in keys:
                raise ValueError("La tabla de productos requiere identificador de rollo")
        else:
            allowed = {self.join_key, "chemistry"} if self.role == "chemistry" else {
                self.join_key, "yield_strength_mpa", "tensile_strength_mpa", "elongation_pct"}
            if self.join_key not in keys or any(c.target not in allowed for c in self.columns):
                raise ValueError("La tabla relacionada requiere clave y columnas compatibles")
            if len(keys) < 2:
                raise ValueError("La tabla relacionada debe incluir al menos un valor")
        return self


class RecognitionAnchor(TemplateModel):
    page_number: int = Field(ge=1, strict=True)
    region: PageRegion
    text: str = Field(min_length=3, max_length=200)

    @model_validator(mode="after")
    def stable_text(self) -> "RecognitionAnchor":
        self.text = " ".join(self.text.split())
        if len(self.text) < 3 or not any(c.isalpha() for c in self.text):
            raise ValueError("Usa un encabezado estable, no sólo números")
        return self


class TemplateConfiguration(TemplateModel):
    schema_version: Literal[1] = 1
    fields: list[FieldMapping] = Field(default_factory=list, max_length=150)
    tables: list[TableMapping] = Field(default_factory=list, max_length=50)
    form: Literal["flat_rolled"] | None = None
    rolling: Literal["cold", "hot"] | None = None
    recognition: list[RecognitionAnchor] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def unambiguous_defaults(self) -> "TemplateConfiguration":
        keys = [field.key for field in self.fields]
        if len(set(keys)) != len(keys):
            raise ValueError("Campos duplicados")
        if self.tables and "product_id" in keys:
            raise ValueError("No combinar un rollo individual con tablas")
        if self.tables and any(field.target == "chemistry" for field in self.fields):
            raise ValueError("La química compartida debe relacionarse por clave mediante una tabla")
        return self

    @property
    def sha256(self) -> str:
        payload = self.model_dump(mode="json")
        # Preserve hashes of stage-1 drafts without recognition anchors.
        if not self.recognition:
            payload.pop("recognition")
        return sha256(json.dumps(payload, sort_keys=True,
                                 separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


class TemplateDiagnostic(TemplateModel):
    code: str
    field: str
    message: str
    page_number: int | None = None


class TemplatePreview(TemplateModel):
    status: Literal["success", "empty", "needs_review", "needs_ocr"]
    certificate: dict[str, JsonValue] | None = None
    evidence: list[dict[str, JsonValue]] = Field(default_factory=list)
    diagnostics: list[TemplateDiagnostic] = Field(default_factory=list)


def extractor_hash() -> str:
    files = (Path(__file__), Path(__file__).with_name("regions.py"), Path(__file__).with_name("template_recognition.py"),
             Path(__file__).with_name("mill_certificate.py"),
             Path(__file__).with_name("measurement_units.py"),
             Path(__file__).parents[1] / "normalization" / "chemistry.py")
    return sha256(b"".join(path.read_bytes() for path in files)).hexdigest()


def preview_template(document: DocumentLayout, configuration: TemplateConfiguration) -> TemplatePreview:
    diagnostics: list[TemplateDiagnostic] = []
    evidence: list[dict[str, JsonValue]] = []
    pages = {page.page_number: page for page in document.pages}
    selected_pages = {item.page_number for item in [*configuration.fields, *configuration.tables]}
    for number in sorted(selected_pages):
        page = pages.get(number)
        if page is None:
            diagnostics.append(TemplateDiagnostic(code="page_missing", field="page", page_number=number,
                                                  message="La página configurada no existe"))
        elif page.source is PageSource.UNREADABLE:
            diagnostics.append(TemplateDiagnostic(code="needs_ocr", field="page", page_number=number,
                                                  message="La página requiere OCR"))
    if diagnostics:
        return TemplatePreview(status="needs_ocr" if any(d.code == "needs_ocr" for d in diagnostics)
                               else "needs_review", diagnostics=diagnostics)

    def issue(code: str, key: str, message: str, number: int | None = None) -> None:
        diagnostics.append(TemplateDiagnostic(code=code, field=key, message=message, page_number=number))

    for page in document.pages:
        if selected_pages and page.page_number not in selected_pages and (page.blocks or page.tables):
            issue("page_not_mapped", "page", "Esta página contiene datos que la plantilla no cubre", page.page_number)

    def value(mapping: ValueMapping, text: str | None, number: int) -> str | float | None:
        if text is None or not text.strip():
            if mapping.required:
                issue("value_missing", mapping.key, "No se encontró un valor", number)
            return None
        text = text.strip()
        if mapping.target in {"thickness_mm", "width_mm", "length_raw"}:
            if mapping.target == "length_raw" and text.upper() in {"C", "COIL", "COILED", "ROLLO"}:
                return "C"
            other_separator = "," if mapping.decimal_separator == "." else "."
            if other_separator in text:
                issue("invalid_number", mapping.key, "La dimensión usa otro separador decimal", number)
                return None
            detected_unit = dimension_unit(text)
            if detected_unit is not None and detected_unit != mapping.unit:
                issue("unit_conflict", mapping.key, "La unidad del valor contradice la configuración", number)
                return None
            result = dimension_value(text, mapping.unit or "", length=mapping.target == "length_raw")
            if result is None:
                issue("invalid_number", mapping.key, "Dimensión no interpretable", number)
            return result
        if mapping.unit is not None:
            decimal = re.escape(mapping.decimal_separator)
            grouping = "," if mapping.decimal_separator == "." else "."
            group = re.escape(grouping)
            if not re.fullmatch(rf"(?:(?:\d+|[1-9]\d{{0,2}}(?:{group}\d{{3}})+)(?:{decimal}\d+)?|{decimal}\d+)", text):
                issue("invalid_number", mapping.key, "Número no interpretable con el separador configurado", number)
                return None
            numeric = Decimal(text.replace(grouping, "").replace(mapping.decimal_separator, "."))
            if not numeric.is_finite() or numeric < 0:
                issue("invalid_number", mapping.key, "El valor debe ser finito y no negativo", number)
                return None
            return str(numeric)
        return text

    defaults: dict[str, JsonValue] = {}
    metadata: dict[str, JsonValue] = {"source_name": document.file_name}

    def assign(row: dict[str, JsonValue], mapping: ValueMapping, raw: str | None, number: int) -> None:
        parsed = value(mapping, raw, number)
        if mapping.target == "chemistry":
            chemistry = row.setdefault("chemistry", {})
            assert isinstance(chemistry, dict) and mapping.element is not None and mapping.exponent is not None
            chemistry[mapping.element] = parsed
            scales = row.setdefault("chemistry_scales", {})
            assert isinstance(scales, dict)
            scales[mapping.element] = mapping.exponent
        else:
            row[mapping.target] = parsed

    for mapping in configuration.fields:
        result = select_region(pages[mapping.page_number], mapping.region)
        evidence.append({"field": mapping.key, "page_number": mapping.page_number,
                         "bbox": result.bbox.as_dict(), "raw_value": result.text, "geometry_scope": "region",
                         "blocks": [{"text": b.text, "bbox": b.bbox.as_dict(), "confidence": b.confidence,
                                     "source": b.source.value} for b in (*result.blocks, *result.partial_blocks)]})
        if result.partial_blocks:
            issue("clipped_text", mapping.key, "La región corta bloques de texto", mapping.page_number)
            continue
        assign(metadata if mapping.target in METADATA_FIELDS else defaults, mapping, result.text, mapping.page_number)

    rows: list[dict[str, JsonValue]] = []
    related: list[tuple[TableMapping, list[dict[str, JsonValue]]]] = []
    for mapping in configuration.tables:
        page = pages[mapping.page_number]
        box = mapping.region.to_bbox(page)
        overlapping = [table for table in page.tables if max(box.x0, table.bbox.x0) < min(box.x1, table.bbox.x1)
                       and max(box.top, table.bbox.top) < min(box.bottom, table.bbox.bottom)]
        if len(overlapping) != 1:
            issue("table_ambiguous", mapping.role, "La región debe contener exactamente una tabla detectada", page.page_number)
            continue
        table = overlapping[0]
        epsilon = 1e-7
        if not (box.x0 - epsilon <= table.bbox.x0 and box.top - epsilon <= table.bbox.top
                and table.bbox.x1 <= box.x1 + epsilon and table.bbox.bottom <= box.bottom + epsilon):
            issue("clipped_table", mapping.role, "La región corta la tabla detectada", page.page_number)
            continue
        if mapping.header_row >= len(table.rows):
            issue("header_missing", mapping.role, "La fila de encabezados no existe", page.page_number)
            continue
        headers = [(cell or "").strip().casefold() for cell in table.rows[mapping.header_row]]
        if any(headers.count(column.header.strip().casefold()) != 1 for column in mapping.columns):
            issue("header_ambiguous", mapping.role, "Faltan encabezados o están duplicados", page.page_number)
            continue
        indexes = [(column, headers.index(column.header.strip().casefold())) for column in mapping.columns]
        extracted: list[dict[str, JsonValue]] = []
        for index, cells in enumerate(table.rows[mapping.header_row + 1:], mapping.header_row + 1):
            if not any(cell and cell.strip() for cell in cells):
                continue
            row = dict(defaults) if mapping.role == "products" else {}
            for nested in ("chemistry", "chemistry_scales"):
                if isinstance(row.get(nested), dict):
                    row[nested] = dict(row[nested])
            row_evidence = []
            for column, position in indexes:
                raw = cells[position] if position < len(cells) else None
                assign(row, column, raw, page.page_number)
                row_evidence.append({"field": column.key, "page_number": page.page_number,
                                 "bbox": table.bbox.as_dict(), "row_index": index,
                                 "header": column.header, "raw_value": raw, "geometry_scope": "table",
                                 "product_id": row.get("product_id"), "heat_no": row.get("heat_no")})
            extracted.append(row)
            for item in row_evidence:
                item["product_id"], item["heat_no"] = row.get("product_id"), row.get("heat_no")
            evidence.extend(row_evidence)
        if mapping.role == "products":
            rows.extend(extracted)
        else:
            related.append((mapping, extracted))
    if not configuration.tables and defaults:
        rows = [defaults]

    for mapping, entries in related:
        seen: set[str] = set()
        counts: dict[str, int] = {}
        for entry in entries:
            key = entry.get(mapping.join_key)
            if isinstance(key, str):
                counts[key] = counts.get(key, 0) + 1
        for entry in entries:
            key = entry.get(mapping.join_key)
            if not isinstance(key, str) or not key or counts[key] != 1:
                issue("join_ambiguous", mapping.join_key, "Clave de relación vacía o duplicada", mapping.page_number)
                continue
            seen.add(key)
            matching = [row for row in rows if row.get(mapping.join_key) == key]
            if not matching:
                issue("join_missing", mapping.join_key, "La fila no corresponde a ningún producto", mapping.page_number)
            for row in matching:
                for field, parsed in entry.items():
                    if field == mapping.join_key:
                        continue
                    if field in {"chemistry", "chemistry_scales"} and isinstance(parsed, dict):
                        existing = row.setdefault(field, {})
                        assert isinstance(existing, dict)
                        for element, observed in parsed.items():
                            if element in existing and existing[element] is not None and existing[element] != observed:
                                issue("join_conflict", f"{field}.{element}", "Valores contradictorios entre tablas", mapping.page_number)
                            else:
                                existing[element] = observed
                        continue
                    if field in row and row[field] is not None and row[field] != parsed:
                        issue("join_conflict", field, "Valores contradictorios entre tablas", mapping.page_number)
                    else:
                        row[field] = parsed
        for row in rows:
            if row.get(mapping.join_key) not in seen:
                issue("join_missing", mapping.join_key, "Producto sin datos en la tabla relacionada", mapping.page_number)
    if not rows:
        return TemplatePreview(status="needs_review" if diagnostics else "empty", evidence=evidence, diagnostics=diagnostics)
    try:
        certificate = normalize_certificate({"document": metadata, "standard": metadata.get("standard"),
                                             "rolling": configuration.rolling, "rows": rows})
    except ValueError as exc:
        issue("normalization_failed", "certificate", str(exc))
        return TemplatePreview(status="needs_review", evidence=evidence, diagnostics=diagnostics)
    evidence_by_product: dict[str, list[dict[str, JsonValue]]] = {}
    evidence_by_heat: dict[str, list[dict[str, JsonValue]]] = {}
    shared_evidence = [item for item in evidence if "row_index" not in item
                       and item.get("field") not in METADATA_FIELDS]
    for item in evidence:
        product_id, heat_no = item.get("product_id"), item.get("heat_no")
        if isinstance(product_id, str):
            evidence_by_product.setdefault(product_id, []).append(item)
        elif isinstance(heat_no, str):
            evidence_by_heat.setdefault(heat_no, []).append(item)
    for product, raw in zip(certificate["products"], rows, strict=True):
        product["form"] = configuration.form
        if raw.get("length_raw") is None:
            product["coiled"] = None
        product["evidence"] = [*evidence_by_product.get(product["product_id"], []),
                               *evidence_by_heat.get(product["heat_no"], []), *shared_evidence]
        for item in product["evidence"]:
            item["page"] = item["page_number"]
            item["region"] = item.get("raw_value")
            key = str(item["field"])
            observation = (product["observations"].get("composition_pct", {}).get(key.split(".", 1)[1])
                           if key.startswith("chemistry.") else product["observations"].get(key))
            if observation is not None:
                observation["raw_value"] = item["raw_value"]
                observation.update(page=item["page_number"], bbox=item["bbox"], source_text=item["raw_value"])
    return TemplatePreview(status="needs_review" if diagnostics else "success", certificate=certificate,
                           evidence=evidence, diagnostics=diagnostics)
