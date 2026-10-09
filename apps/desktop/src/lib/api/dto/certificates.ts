import type { ApprovalStatusDto } from "./classification";
import type { JsonValue } from "./common";

export interface CertificateDeletionDto {
  certificate_id: number;
  document_id: number;
  deleted: true;
}

export interface CertificateHeatDto {
  id: number;
  heat_no: string | null;
  standard: string | null;
  grade: string | null;
}

export interface CertificateProductDto {
  id: number;
  heat_id: number | null;
  product_identifier: string | null;
  label_no: string | null;
  product_type: string | null;
  form: string | null;
  coiled: boolean | null;
  rolling: string | null;
  width_mm: string | null;
  thickness_mm: string | null;
  weight_kg: string | null;
}

export interface CertificateObservationDto {
  verification?: FieldVerificationDto | null;
  id: number;
  heat_id: number | null;
  product_id: number | null;
  field_path: string;
  raw_value: JsonValue;
  normalized_value: JsonValue;
  unit: string | null;
  confidence: number | null;
  page_number: number | null;
  bbox: JsonValue;
  source_text: string | null;
  inherited: boolean;
  supersedes_id: number | null;
  is_current: boolean;
}

export interface FieldVerificationDto {
  status: "matches" | "discrepancy" | "not_verifiable" | "error";
  model: string;
  raw_value: string | null;
  normalized_value: number | null;
  unit: string | null;
  page_number: number | null;
  bbox: Record<string, number> | null;
  source_id: string | null;
  source_text: string | null;
  header_id: string | null;
  header_text: string | null;
  header_bbox: Record<string, number> | null;
  error_code: string | null;
}

export interface CertificateChemicalCompositionDto {
  id: number;
  heat_id: number | null;
  product_id: number | null;
  element: string;
  raw_value: JsonValue;
  percentage: string | null;
  inherited: boolean;
  source_label: string | null;
}

/** `GET /api/v1/certificates/{id}` */
export interface CertificateDetailDto {
  id: number;
  document_id: number;
  manufacturer: string | null;
  certificate_no: string | null;
  certificate_date: string | null;
  uploaded_at: string;
  revision_number: number;
  previous_revision_id: number | null;
  approval_status: ApprovalStatusDto;
  standard: string | null;
  product_name: string | null;
  demo_notice: string;
  heats: readonly CertificateHeatDto[];
  products: readonly CertificateProductDto[];
  observations: readonly CertificateObservationDto[];
  chemical_compositions: readonly CertificateChemicalCompositionDto[];
}
