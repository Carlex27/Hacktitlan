const DEFAULT_API_BASE_URL = "http://127.0.0.1:8765";

/** Normaliza la URL base del backend y elimina barras finales. */
export function resolveApiBaseUrl(configured: string | undefined): string {
  const value = configured?.trim();
  const base = value && value.length > 0 ? value : DEFAULT_API_BASE_URL;
  return base.replace(/\/+$/, "");
}
