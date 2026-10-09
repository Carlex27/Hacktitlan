import type { ApiClient, RequestOptions } from "../client";
import type {
  ActorReasonDto,
  CandidateSelectionDto,
  CandidateSelectionRequestDto,
  ClassificationCandidateDetailDto,
  ClassificationRunDto,
  ClassificationRunSummaryDto,
  RunApprovalResultDto,
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

/** Aprueba formalmente una ejecución de clasificación con persona y motivo. */
export async function approveClassificationRun(
  api: ApiClient,
  runId: number,
  request: ActorReasonDto,
  options?: RequestOptions,
) {
  return (
    await api.post<RunApprovalResultDto>(
      `/api/v1/classification-runs/${runId}/approve`,
      request,
      options,
    )
  ).data;
}

/** Rechaza formalmente una ejecución de clasificación con persona y motivo. */
export async function rejectClassificationRun(
  api: ApiClient,
  runId: number,
  request: ActorReasonDto,
  options?: RequestOptions,
) {
  return (
    await api.post<RunApprovalResultDto>(
      `/api/v1/classification-runs/${runId}/reject`,
      request,
      options,
    )
  ).data;
}

/** Detalle de un candidato con sus factores y evidencia. */
export async function getClassificationCandidate(
  api: ApiClient,
  candidateId: number,
  options?: RequestOptions,
) {
  return (
    await api.get<ClassificationCandidateDetailDto>(
      `/api/v1/classification-candidates/${candidateId}`,
      options,
    )
  ).data;
}
