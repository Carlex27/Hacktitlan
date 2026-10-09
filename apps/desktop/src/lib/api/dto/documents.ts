import type { JsonObject } from "./common";

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
  result: JsonObject | null;
}
