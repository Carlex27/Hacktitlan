import type { ActorReasonDto, JsonObject, JsonValue } from "./common";

export type QualityCategoryDto = "missing" | "low_confidence" | "contradiction" | "anomaly";

export type QualitySeverityDto = "blocking" | "warning";

export type ProductFamilyDto =
  | "flat_rolled_coil"
  | "flat_rolled_plate"
  | "flat_rolled_general"
  | "unknown";

export interface QualityIssueDto {
  code: string;
  category: QualityCategoryDto;
  severity: QualitySeverityDto;
  scope: string;
  field_path: string;
  message: string;
  entity_identifier: string | null;
  raw_value: JsonValue;
  normalized_value: JsonValue;
  confidence: number | null;
  page_number: number | null;
  bbox: JsonObject | null;
}

/** `GET /api/v1/certificates/{id}/quality-report`. */
export interface DocumentQualityReportDto {
  certificate_id: number | null;
  status: string;
  quality_score: number;
  product_family: ProductFamilyDto;
  blocking_count: number;
  warning_count: number;
  provenance_summary: Readonly<Record<string, number>>;
  issues: readonly QualityIssueDto[];
}

export interface DocumentReviewIssueSummaryDto {
  code: string;
  category: QualityCategoryDto;
  severity: QualitySeverityDto;
  field_path: string;
  message: string;
}

/** Elemento de `GET /api/v1/document-reviews`. */
export interface DocumentReviewQueueItemDto {
  source_file_name: string | null;
  /** Revisión del acta; reprocesar desde extracción crea la siguiente. */
  revision_number: number;
  /** Trabajo de extracción en cola o en curso; mientras exista no se puede reprocesar. */
  active_job_id: number | null;
  can_reprocess: boolean;
  certificate_id: number;
  document_id: number;
  certificate_no: string | null;
  manufacturer: string | null;
  uploaded_at: string;
  document_status: string;
  approval_status: string;
  quality_score: number;
  blocking_issues_count: number;
  warning_issues_count: number;
  issues_summary: readonly DocumentReviewIssueSummaryDto[];
}

export type ReprocessStageDto = "extraction" | "normalization" | "classification";

/**
 * Cuerpo de `POST /api/v1/certificates/{id}/reprocess`. Si ya hay una
 * extracción activa responde 409 `reprocess_in_progress` con `details.job_id`.
 */
export interface ReprocessRequestDto extends ActorReasonDto {
  from_stage: ReprocessStageDto;
}

export interface ReprocessResultDto {
  /** Desde `extraction` el backend crea una revisión nueva del acta con otro id. */
  certificate_id: number;
  job_id: number | null;
  stage: ReprocessStageDto;
  status: string;
  quality_report: DocumentQualityReportDto | null;
}
