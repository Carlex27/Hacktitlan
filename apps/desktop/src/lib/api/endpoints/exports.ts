import type { ApiClient, RequestOptions } from "../client";
import type { ExportCreatedDto, ExportRequestDto, ExportStatusDto } from "../dto";

/** Encola un libro XLSX; seguir con `getExport` o el `job_id` devuelto. */
export async function createExport(
  api: ApiClient,
  request: ExportRequestDto,
  options?: RequestOptions,
) {
  return (await api.post<ExportCreatedDto>("/api/v1/exports", request, options)).data;
}

export async function getExport(api: ApiClient, exportId: number, options?: RequestOptions) {
  return (await api.get<ExportStatusDto>(`/api/v1/exports/${exportId}`, options)).data;
}
