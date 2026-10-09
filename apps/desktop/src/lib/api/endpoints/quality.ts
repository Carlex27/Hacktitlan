import type { ApiClient, RequestOptions } from "../client";
import type {
  DocumentQualityReportDto,
  DocumentReviewQueueItemDto,
  ReprocessRequestDto,
  ReprocessResultDto,
} from "../dto";

export async function getCertificateQualityReport(
  api: ApiClient,
  certificateId: number,
  options?: RequestOptions,
) {
  return (
    await api.get<DocumentQualityReportDto>(
      `/api/v1/certificates/${certificateId}/quality-report`,
      options,
    )
  ).data;
}

export interface DocumentReviewQuery {
  limit?: number;
  statusFilter?: string;
}

/** Cola de actas con incidencias de calidad pendientes de revisión. */
export async function listDocumentReviews(
  api: ApiClient,
  query: DocumentReviewQuery = {},
  options?: RequestOptions,
) {
  const params = new URLSearchParams();
  if (query.limit !== undefined) params.set("limit", String(query.limit));
  if (query.statusFilter) params.set("status_filter", query.statusFilter);
  const search = params.size > 0 ? `?${params.toString()}` : "";
  return (
    await api.get<DocumentReviewQueueItemDto[]>(`/api/v1/document-reviews${search}`, options)
  ).data;
}

/** Reprocesa un acta desde la etapa indicada; registra persona y motivo. */
export async function reprocessCertificate(
  api: ApiClient,
  certificateId: number,
  request: ReprocessRequestDto,
  options?: RequestOptions,
) {
  return (
    await api.post<ReprocessResultDto>(
      `/api/v1/certificates/${certificateId}/reprocess`,
      request,
      options,
    )
  ).data;
}
