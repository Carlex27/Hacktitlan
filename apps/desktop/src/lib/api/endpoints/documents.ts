import type { ApiClient, RequestOptions } from "../client";
import type { ActorReasonDto, JobDto, UploadDocumentDto } from "../dto";

export async function uploadDocument(api: ApiClient, file: File, options?: RequestOptions) {
  const form = new FormData();
  form.append("file", file, file.name);
  return (await api.postForm<UploadDocumentDto>("/api/v1/documents", form, options)).data;
}

export async function getJob(api: ApiClient, jobId: number, options?: RequestOptions) {
  return (await api.get<JobDto>(`/api/v1/jobs/${jobId}`, options)).data;
}

export async function archiveDocument(api: ApiClient, documentId: number, request: ActorReasonDto & { archived: boolean }) {
  await api.post<unknown>(`/api/v1/documents/${documentId}/archive`, request);
}
