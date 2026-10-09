import type { ApiClient, RequestOptions } from "../client";
import type { OcrModelPackageStatusDto, OcrSmokeCheckDto, OcrStatusDto } from "../dto";

export async function getOcrStatus(api: ApiClient, options?: RequestOptions) {
  return (await api.get<OcrStatusDto>("/api/v1/ocr/status", options)).data;
}

export async function getOcrModels(api: ApiClient, options?: RequestOptions) {
  return (await api.get<OcrModelPackageStatusDto>("/api/v1/ocr/models", options)).data;
}

/** Ejecuta una prueba corta del OCR instalado en el servidor. */
export async function runOcrSmokeCheck(api: ApiClient, options?: RequestOptions) {
  return (await api.post<OcrSmokeCheckDto>("/api/v1/ocr/smoke-check", {}, options)).data;
}
