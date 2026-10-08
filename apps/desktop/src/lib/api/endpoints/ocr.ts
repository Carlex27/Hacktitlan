import type { ApiClient, RequestOptions } from "../client";
import type { OcrStatusDto } from "../dto";

export async function getOcrStatus(api: ApiClient, options?: RequestOptions) {
  return (await api.get<OcrStatusDto>("/api/v1/ocr/status", options)).data;
}
