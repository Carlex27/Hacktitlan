import type { JobDto, JobStatusDto, UploadDocumentDto } from "@/lib/api";
import type { ProcessingStatus } from "@/types";

/** Etapa de un archivo dentro del flujo de importación. */
export type ImportPhase =
  | "uploading"
  | JobStatusDto
  /** El servidor aceptó el archivo pero no devolvió un trabajo asociado. */
  | "no_job"
  /** La carga o la consulta del trabajo falló en la comunicación. */
  | "request_failed";

export interface ImportItem {
  id: string;
  fileName: string;
  phase: ImportPhase;
  /** Progreso informado por el servidor; `null` si no se conoce. */
  progress: number | null;
  certificateId: number | null;
  documentId: number | null;
  jobId: number | null;
  duplicate: boolean;
  /** Mensaje del servidor o del cliente cuando el flujo falla. */
  errorMessage: string | null;
}

const TERMINAL_PHASES: ReadonlySet<ImportPhase> = new Set<ImportPhase>([
  "succeeded",
  "needs_review",
  "needs_ocr",
  "failed",
  "cancelled",
  "no_job",
  "request_failed",
]);

export function isTerminalPhase(phase: ImportPhase): boolean {
  return TERMINAL_PHASES.has(phase);
}

export function visibleImportItems(items: readonly ImportItem[]): readonly ImportItem[] {
  return items.filter((item) => item.phase !== "succeeded" && item.phase !== "needs_review");
}

export function completedImportKey(items: readonly ImportItem[]): string {
  return items.filter((item) => item.phase === "succeeded" || item.phase === "needs_review").map((item) => item.id).join(",");
}

export function phaseToStatus(phase: ImportPhase): ProcessingStatus {
  switch (phase) {
    case "uploading":
    case "queued":
    case "running":
      return "loading";
    case "succeeded":
      return "success";
    case "needs_review":
    case "needs_ocr":
    case "no_job":
      return "needs_review";
    case "failed":
    case "cancelled":
    case "request_failed":
      return "error";
  }
}

export function createImportItem(id: string, fileName: string): ImportItem {
  return {
    id,
    fileName,
    phase: "uploading",
    progress: null,
    certificateId: null,
    documentId: null,
    jobId: null,
    duplicate: false,
    errorMessage: null,
  };
}

export function applyUpload(item: ImportItem, upload: UploadDocumentDto): ImportItem {
  return {
    ...item,
    phase: upload.job_id === null ? "no_job" : "queued",
    certificateId: upload.certificate_id,
    documentId: upload.document_id,
    jobId: upload.job_id,
    duplicate: upload.duplicate,
  };
}

export function applyJob(item: ImportItem, job: JobDto): ImportItem {
  return {
    ...item,
    phase: job.status,
    progress: job.progress,
    errorMessage: job.error_message,
  };
}

export function applyFailure(item: ImportItem, message: string): ImportItem {
  return { ...item, phase: "request_failed", errorMessage: message };
}
