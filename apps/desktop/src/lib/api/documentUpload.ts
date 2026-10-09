import { request } from "./documentReviews";

// Transport contract: DocumentUploadRead in the generated OpenAPI schema.
export interface DocumentUpload {
  document_id: number;
  certificate_id: number;
  job_id: number | null;
  duplicate: boolean;
}

export function uploadDocument(baseUrl: string, file: File): Promise<DocumentUpload> {
  const body = new FormData();
  body.append("file", file);
  return request(baseUrl, "/documents", { method: "POST", body });
}
