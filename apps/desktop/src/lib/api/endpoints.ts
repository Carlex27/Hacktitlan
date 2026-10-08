import type { ApiClient, RequestOptions } from "./client";
import type { HealthLiveDto, HealthReadyDto, JobDto, UploadDocumentDto } from "./dto";

export async function getHealthLive(api: ApiClient, options?: RequestOptions) {
  return (await api.get<HealthLiveDto>("/api/v1/health/live", options)).data;
}

export async function getHealthReady(api: ApiClient, options?: RequestOptions) {
  return (await api.get<HealthReadyDto>("/api/v1/health/ready", options)).data;
}

export async function uploadDocument(api: ApiClient, file: File, options?: RequestOptions) {
  const form = new FormData();
  form.append("file", file, file.name);
  return (await api.postForm<UploadDocumentDto>("/api/v1/documents", form, options)).data;
}

export async function getJob(api: ApiClient, jobId: number, options?: RequestOptions) {
  return (await api.get<JobDto>(`/api/v1/jobs/${jobId}`, options)).data;
}
