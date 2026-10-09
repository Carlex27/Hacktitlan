import { ApiError } from "./errors";

export interface ApiEnvelope<T> {
  data: T;
  meta: Readonly<Record<string, unknown>>;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

/**
 * Valida el sobre `{ data, meta, error }` del backend. No valida la forma de
 * `data`: cada endpoint declara su DTO y el backend es la fuente de verdad.
 */
export function parseEnvelope<T>(
  body: unknown,
  status: number,
  requestId: string | undefined,
): ApiEnvelope<T> {
  if (!isRecord(body) || !("data" in body) || !("error" in body)) {
    throw new ApiError({
      kind: "invalid_response",
      message: "La respuesta del servidor no tiene el formato esperado.",
      status,
      requestId,
    });
  }

  const { error } = body;
  if (error !== null) {
    const payload = isRecord(error) ? error : {};
    throw new ApiError({
      kind: "server",
      code: typeof payload.code === "string" ? payload.code : undefined,
      message:
        typeof payload.message === "string"
          ? payload.message
          : "El servidor devolvió un error sin descripción.",
      details: isRecord(payload.details) ? payload.details : undefined,
      status,
      requestId,
    });
  }

  if (status >= 400) {
    throw new ApiError({
      kind: "invalid_response",
      message: "El servidor devolvió un error sin descripción.",
      status,
      requestId,
    });
  }

  return {
    data: body.data as T,
    meta: isRecord(body.meta) ? body.meta : {},
  };
}
