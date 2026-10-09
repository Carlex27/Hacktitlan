import { parseEnvelope, type ApiEnvelope } from "./envelope";
import { ApiError } from "./errors";

export type FetchLike = (input: string, init?: RequestInit) => Promise<Response>;

export interface ApiClientOptions {
  baseUrl: string;
  fetch?: FetchLike;
  createRequestId?: () => string;
}

export interface RequestOptions {
  signal?: AbortSignal | undefined;
}

export interface ApiClient {
  readonly baseUrl: string;
  /** URL absoluta para rutas relativas del API (p. ej. `file_url`, `detail_url`). */
  url(path: string): string;
  get<T>(path: string, options?: RequestOptions): Promise<ApiEnvelope<T>>;
  delete<T>(path: string, options?: RequestOptions): Promise<ApiEnvelope<T>>;
  post<T>(path: string, body: unknown, options?: RequestOptions): Promise<ApiEnvelope<T>>;
  postForm<T>(path: string, form: FormData, options?: RequestOptions): Promise<ApiEnvelope<T>>;
  /** Descarga un archivo (p. ej. un PDF). Los errores llegan como `ApiError`. */
  getBlob(path: string, options?: RequestOptions): Promise<Blob>;
}

function defaultRequestId(): string {
  return crypto.randomUUID().replaceAll("-", "");
}

export function createApiClient({
  baseUrl,
  fetch: fetchImpl = (input, init) => globalThis.fetch(input, init),
  createRequestId = defaultRequestId,
}: ApiClientOptions): ApiClient {
  async function send(path: string, init: RequestInit): Promise<{ response: Response; requestId: string }> {
    const requestId = createRequestId();
    const headers = new Headers(init.headers);
    headers.set("X-Request-ID", requestId);

    let response: Response;
    try {
      response = await fetchImpl(`${baseUrl}${path}`, { ...init, headers });
    } catch (cause) {
      if (init.signal?.aborted) {
        throw new ApiError({ kind: "aborted", message: "Solicitud cancelada.", requestId });
      }
      throw new ApiError({
        kind: "network",
        message:
          cause instanceof Error ? cause.message : "No fue posible conectar con el servidor.",
        requestId,
      });
    }
    return { response, requestId: response.headers.get("X-Request-ID") ?? requestId };
  }

  async function readEnvelope<T>(response: Response, requestId: string): Promise<ApiEnvelope<T>> {
    let body: unknown;
    try {
      body = await response.json();
    } catch {
      throw new ApiError({
        kind: "invalid_response",
        message: "La respuesta del servidor no es JSON válido.",
        status: response.status,
        requestId,
      });
    }
    return parseEnvelope<T>(body, response.status, requestId);
  }

  async function request<T>(path: string, init: RequestInit): Promise<ApiEnvelope<T>> {
    const { response, requestId } = await send(path, init);
    return readEnvelope<T>(response, requestId);
  }

  async function getBlob(path: string, options?: RequestOptions): Promise<Blob> {
    const { response, requestId } = await send(path, { method: "GET", signal: options?.signal ?? null });
    if (!response.ok) {
      // Los errores del API llegan en el sobre JSON; se reportan igual que el resto.
      await readEnvelope<unknown>(response, requestId);
      throw new ApiError({
        kind: "invalid_response",
        message: "El servidor no devolvió el archivo.",
        status: response.status,
        requestId,
      });
    }
    return response.blob();
  }

  return {
    baseUrl,
    url: (path) => `${baseUrl}${path}`,
    get: (path, options) => request(path, { method: "GET", signal: options?.signal ?? null }),
    delete: (path, options) => request(path, { method: "DELETE", signal: options?.signal ?? null }),
    post: (path, body, options) =>
      request(path, {
        method: "POST",
        body: JSON.stringify(body),
        headers: { "Content-Type": "application/json" },
        signal: options?.signal ?? null,
      }),
    postForm: (path, form, options) =>
      request(path, { method: "POST", body: form, signal: options?.signal ?? null }),
    getBlob,
  };
}
