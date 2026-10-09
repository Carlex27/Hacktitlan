import type { JsonObject, JsonValue } from "./common";
import type { JobStatusDto } from "./documents";

export interface RegionDto { x0: number; top: number; x1: number; bottom: number }
export type MappingTargetDto = "certificate_no" | "supplier" | "standard" | "product_id" | "heat_no" |
  "thickness_mm" | "width_mm" | "length_raw" | "weight_kg" | "yield_strength_mpa" | "tensile_strength_mpa" | "elongation_pct" | "chemistry";
export interface ValueMappingDto {
  target: MappingTargetDto; element: string | null; unit: "mm" | "cm" | "in" | "ft" | "m" | "kg" | "MPa" | "%" | null;
  exponent: number | null; required: boolean; decimal_separator: "." | ",";
}
export interface FieldMappingDto extends ValueMappingDto { page_number: number; region: RegionDto }
export interface ColumnMappingDto extends ValueMappingDto { header: string }
export interface TableMappingDto {
  page_number: number; region: RegionDto; role: "products" | "chemistry" | "mechanical";
  join_key: "product_id" | "heat_no"; header_row: number; columns: ColumnMappingDto[];
}
export interface RecognitionAnchorDto { page_number: number; region: RegionDto; text: string }
export interface TemplateConfigurationDto {
  schema_version: 1; fields: FieldMappingDto[]; tables: TableMappingDto[]; recognition: RecognitionAnchorDto[];
  form: "flat_rolled" | null; rolling: "cold" | "hot" | null;
}
export interface FormatDto { id: number; name: string; description: string }
export interface FormatVersionDto {
  id: number; format_id: number; version_number: number; revision: number; status: "draft" | "active" | "retired";
  configuration: TemplateConfigurationDto; configuration_sha256: string; person_name: string; reason: string;
  updated_at: string; lifecycle: JsonObject[];
}
export interface FormatDetailDto extends FormatDto { versions: FormatVersionDto[] }
export interface PageLayoutDto {
  page_number: number; width: number; height: number; rotation: number; source: "digital" | "ocr" | "unreadable";
  blocks: { text: string; bbox: RegionDto; confidence: number; page_number: number; source: string }[];
  tables: { bbox: RegionDto; rows: (string | null)[][]; page_number: number }[];
}
export interface LayoutDto {
  id: number; document_id: number; document_sha256: string;
  document: { file_name: string; sha256: string; pages: PageLayoutDto[]; metadata: JsonObject };
}
export interface FormatTestDto {
  id: number; version_id: number; document_id: number; layout_id: number; job_id: number | null; revision: number;
  configuration_sha256: string; extractor_sha256: string; status: JobStatusDto; current_revision: boolean;
  reviewed_by: string | null; review_reason: string | null;
  result: { status: "success" | "empty" | "needs_review" | "needs_ocr"; certificate: JsonObject | null;
    evidence: JsonObject[]; diagnostics: { code: string; field: string; message: string; page_number: number | null }[] } | null;
}
export type FormatValueDto = JsonValue;
