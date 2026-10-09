import { request } from "./documentReviews";

// Transport contract: JobRead in the generated OpenAPI schema.
export interface DocumentJob {
  id: number;
  document_id: number | null;
  status: "queued" | "running" | "succeeded" | "needs_review" | "needs_ocr" | "failed" | "cancelled";
  progress: number;
  attempts: number;
  error_message: string | null;
}

export function getDocumentJob(baseUrl: string, id: number, signal?: AbortSignal): Promise<DocumentJob> {
  return request(baseUrl, `/jobs/${id}`, { signal: signal ?? null });
}
