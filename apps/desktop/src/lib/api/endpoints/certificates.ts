import type { ApiClient, RequestOptions } from "../client";
import type { CertificateDetailDto } from "../dto";

export async function getCertificate(
  api: ApiClient,
  certificateId: number,
  options?: RequestOptions,
): Promise<CertificateDetailDto> {
  return (
    await api.get<CertificateDetailDto>(`/api/v1/certificates/${certificateId}`, options)
  ).data;
}
