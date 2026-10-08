/**
 * Tipos de transporte del API v1. Reflejan exactamente las respuestas del
 * backend (snake_case); los modelos de vista viven en cada feature.
 */

export interface HealthLiveDto {
  status: "ok";
}

export interface HealthReadyDto {
  status: "ready";
  database: string;
  storage: string;
}

export interface UploadDocumentDto {
  document_id: number;
  certificate_id: number;
  /** Puede faltar si el documento duplicado no tiene trabajos registrados. */
  job_id: number | null;
  duplicate: boolean;
}

export type JobStatusDto =
  | "queued"
  | "running"
  | "succeeded"
  | "needs_review"
  | "needs_ocr"
  | "failed"
  | "cancelled";

export interface JobDto {
  id: number;
  document_id: number | null;
  kind: string;
  status: JobStatusDto;
  progress: number | null;
  attempts: number;
  max_attempts: number;
  error_code: string | null;
  error_message: string | null;
  result: Readonly<Record<string, unknown>> | null;
}
