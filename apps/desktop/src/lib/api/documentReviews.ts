export interface DocumentReview {
  certificate_id: number;
  certificate_no: string | null;
  revision_number: number;
  document_status: string;
  active_job_id: number | null;
  can_reprocess: boolean;
}

interface Envelope<T> {
  data: T;
  error: { message: string } | null;
}

async function request<T>(baseUrl: string, path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${baseUrl.replace(/\/$/, "")}/api/v1${path}`, init);
  const envelope: Envelope<T> = await response.json();
  if (!response.ok || envelope.error) {
    throw new Error(envelope.error?.message ?? `HTTP ${response.status}`);
  }
  return envelope.data;
}

export function getDocumentReviews(baseUrl: string): Promise<DocumentReview[]> {
  return request(baseUrl, "/document-reviews");
}

export function reprocessDocument(baseUrl: string, certificateId: number, personName: string, reason: string) {
  return request<{ job_id: number; certificate_id: number }>(baseUrl, `/certificates/${certificateId}/reprocess`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ from_stage: "extraction", person_name: personName, reason }),
  });
}
