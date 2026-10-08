import type { ApiClient, RequestOptions } from "../client";
import type { EvidenceDetailDto } from "../dto";

export async function getEvidence(api: ApiClient, evidenceLinkId: number, options?: RequestOptions) {
  return (await api.get<EvidenceDetailDto>(`/api/v1/evidence/${evidenceLinkId}`, options)).data;
}
