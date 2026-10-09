import { ApiError } from "@/lib/api";

/**
 * `true` si el servidor no publica la ruta de referencia LIGIE (404 genérico de
 * ruta inexistente). Un código inexistente llega como `not_found` y no cuenta aquí.
 */
export function isReferenceUnsupported(error: unknown): boolean {
  return error instanceof ApiError && error.status === 404 && error.code === "http_error";
}
