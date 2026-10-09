import type { DocumentReviewQueueItemDto } from "@/lib/api";
import type { ProcessingStatus } from "@/types";

/** Estado visual de una revisión: un trabajo activo tiene prioridad sobre las incidencias. */
export function reviewItemStatus(item: DocumentReviewQueueItemDto): ProcessingStatus {
  if (item.active_job_id !== null) return "loading";
  if (item.blocking_issues_count > 0 || item.warning_issues_count > 0) return "needs_review";
  return "success";
}

export interface ReprocessFormErrors {
  person?: string;
  reason?: string;
}

/** Mismas reglas mínimas que exige el backend para persona y motivo. */
export function validateReprocessForm(
  person: string,
  reason: string,
  messages: { personRequired: string; reasonRequired: string },
): ReprocessFormErrors {
  const errors: ReprocessFormErrors = {};
  if (person.trim().length < 2) errors.person = messages.personRequired;
  if (reason.trim().length < 3) errors.reason = messages.reasonRequired;
  return errors;
}
