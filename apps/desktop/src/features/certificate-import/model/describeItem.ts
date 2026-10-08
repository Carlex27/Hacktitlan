import { es } from "@/lib/i18n";

import type { ImportItem, ImportPhase } from "./importItem";

const PHASE_TEXT: Record<ImportPhase, string> = {
  uploading: es.certificateImport.item.uploading,
  queued: es.certificateImport.item.queued,
  running: es.certificateImport.item.running,
  succeeded: es.certificateImport.item.succeeded,
  needs_review: es.certificateImport.item.needsReview,
  needs_ocr: es.certificateImport.item.needsOcr,
  failed: es.certificateImport.item.failed,
  cancelled: es.certificateImport.item.cancelled,
  no_job: es.certificateImport.item.noJob,
  request_failed: es.errors.unexpected,
};

/** Texto principal de la fila; los errores muestran el mensaje recibido. */
export function describeItem(item: ImportItem): string {
  if (item.phase === "request_failed" && item.errorMessage) return item.errorMessage;
  return PHASE_TEXT[item.phase];
}
