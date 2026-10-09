import type { ApiClient, RequestOptions } from "../client";
import type { ActorReasonDto, CertificateDeletionDto, CertificateDetailDto } from "../dto";

export async function acceptFieldVerification(api: ApiClient, observationId: number, actor: ActorReasonDto) {
  return (await api.post<{ observation_id: number; supersedes_id: number }>(
    `/api/v1/observations/${observationId}/corrections`, { ...actor, accept_verification: true },
  )).data;
}

export async function deleteCertificate(api: ApiClient, certificateId: number) {
  return (await api.delete<CertificateDeletionDto>(`/api/v1/certificates/${certificateId}`)).data;
}

export type CertificateSummaryDto = Pick<CertificateDetailDto,
  "id" | "document_id" | "source_file_name" | "certificate_no" | "manufacturer" | "approval_status" | "certificate_date">;

export interface CertificateFilters {
  certificate_no?: string;
  manufacturer?: string;
  heat_no?: string;
  product_identifier?: string;
  fraction?: string;
  nico?: string;
  date_from?: string;
  date_to?: string;
  approval_status?: CertificateDetailDto["approval_status"] | "";
}

export function listCertificates(api: ApiClient, cursor: string | null, options?: RequestOptions, filters: CertificateFilters = {}) {
  const query = new URLSearchParams();
  if (cursor !== null) query.set("cursor", cursor);
  for (const [key, value] of Object.entries(filters)) if (value) query.set(key, value);
  const suffix = query.size ? `?${query}` : "";
  return api.get<readonly CertificateSummaryDto[]>(`/api/v1/certificates${suffix}`, options);
}

export async function getCertificate(
  api: ApiClient,
  certificateId: number,
  options?: RequestOptions,
): Promise<CertificateDetailDto> {
  return (
    await api.get<CertificateDetailDto>(`/api/v1/certificates/${certificateId}`, options)
  ).data;
}
