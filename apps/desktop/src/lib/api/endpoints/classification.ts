import type { ApiClient, RequestOptions } from "../client";
import type {
  CandidateSelectionDto,
  CandidateSelectionRequestDto,
  ClassificationRunDto,
  ClassificationRunSummaryDto,
} from "../dto";

export async function listClassificationRuns(
  api: ApiClient,
  certificateId: number,
  options?: RequestOptions,
) {
  return (
    await api.get<ClassificationRunSummaryDto[]>(
      `/api/v1/certificates/${certificateId}/classification-runs`,
      options,
    )
  ).data;
}

export async function getClassificationRun(api: ApiClient, runId: number, options?: RequestOptions) {
  return (await api.get<ClassificationRunDto>(`/api/v1/classification-runs/${runId}`, options)).data;
}

/** Registra qué candidato (fracción + NICO) elige una persona para un resultado. */
export async function selectClassificationCandidate(
  api: ApiClient,
  resultId: number,
  request: CandidateSelectionRequestDto,
  options?: RequestOptions,
) {
  return (
    await api.post<CandidateSelectionDto>(
      `/api/v1/classification-results/${resultId}/select`,
      request,
      options,
    )
  ).data;
}
