import type { ApiClient, RequestOptions } from "../client";
import type { ActorReasonDto } from "../dto/common";
import type { FormatDto, FormatDetailDto, FormatVersionDto, FormatTestDto, LayoutDto, TemplateConfigurationDto } from "../dto/formats";

export const listFormats = async (api: ApiClient, offset = 0, options?: RequestOptions, query = "") =>
  (await api.get<FormatDto[]>(`/api/v1/certificate-formats?limit=50&offset=${offset}${query ? `&q=${encodeURIComponent(query)}` : ""}`, options)).data;
export const getFormat = async (api: ApiClient, id: number, options?: RequestOptions) =>
  (await api.get<FormatDetailDto>(`/api/v1/certificate-formats/${id}`, options)).data;
export const createFormat = async (api: ApiClient, name: string, actor: ActorReasonDto) =>
  (await api.post<FormatDto>("/api/v1/certificate-formats", { name, ...actor })).data;
export const saveFormatVersion = async (api: ApiClient, version: FormatVersionDto, configuration: TemplateConfigurationDto, actor: ActorReasonDto) =>
  (await api.patch<FormatVersionDto>(`/api/v1/certificate-format-versions/${version.id}`,
    { expected_revision: version.revision, configuration, ...actor })).data;
export const newFormatVersion = async (api: ApiClient, version: FormatVersionDto, actor: ActorReasonDto) =>
  (await api.post<FormatVersionDto>(`/api/v1/certificate-formats/${version.format_id}/versions`, { configuration: version.configuration, ...actor })).data;
export const transitionFormat = async (api: ApiClient, version: FormatVersionDto, action: "activate" | "retire", actor: ActorReasonDto) =>
  (await api.post<FormatVersionDto>(`/api/v1/certificate-format-versions/${version.id}/${action}`, { expected_revision: version.revision, ...actor })).data;
export const prepareFormatLayout = async (api: ApiClient, documentId: number, actor: ActorReasonDto) =>
  (await api.post<{ job_id: number }>(`/api/v1/documents/${documentId}/layout-jobs`, actor)).data;
export const getFormatLayout = async (api: ApiClient, documentId: number, options?: RequestOptions) =>
  (await api.get<LayoutDto>(`/api/v1/documents/${documentId}/layout`, options)).data;
export const getPreparedLayout = async (api: ApiClient, layoutId: number, options?: RequestOptions) =>
  (await api.get<LayoutDto>(`/api/v1/document-layouts/${layoutId}`, options)).data;
export const listFormatTests = async (api: ApiClient, versionId: number, options?: RequestOptions) =>
  (await api.get<FormatTestDto[]>(`/api/v1/certificate-format-versions/${versionId}/tests`, options)).data;
export const getFormatTest = async (api: ApiClient, id: number, options?: RequestOptions) =>
  (await api.get<FormatTestDto>(`/api/v1/certificate-format-tests/${id}`, options)).data;
export const runFormatTest = async (api: ApiClient, version: FormatVersionDto, layoutId: number, actor: ActorReasonDto) =>
  (await api.post<FormatTestDto>(`/api/v1/certificate-format-versions/${version.id}/tests`, { expected_revision: version.revision, layout_id: layoutId, ...actor })).data;
export const confirmFormatTest = async (api: ApiClient, id: number, actor: ActorReasonDto) =>
  (await api.post<FormatTestDto>(`/api/v1/certificate-format-tests/${id}/confirm`, actor)).data;
export const applyFormat = async (api: ApiClient, certificateId: number, versionId: number, actor: ActorReasonDto) =>
  (await api.post<{ certificate_id: number; job_id: number }>(`/api/v1/certificates/${certificateId}/reprocess`,
    { from_stage: "extraction", format_version_id: versionId, ...actor })).data;
