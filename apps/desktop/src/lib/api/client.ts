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
  get<T>(path: string, options?: RequestOptions): Promise<ApiEnvelope<T>>;
  postForm<T>(path: string, form: FormData, options?: RequestOptions): Promise<ApiEnvelope<T>>;
}

function defaultRequestId(): string {
  return crypto.randomUUID().replaceAll("-", "");
}

export function createApiClient({
  baseUrl,
  fetch: fetchImpl = (input, init) => globalThis.fetch(input, init),
  createRequestId = defaultRequestId,
}: ApiClientOptions): ApiClient {
  async function request<T>(path: string, init: RequestInit): Promise<ApiEnvelope<T>> {
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

    const responseId = response.headers.get("X-Request-ID") ?? requestId;
    let body: unknown;
    try {
      body = await response.json();
    } catch {
      throw new ApiError({
        kind: "invalid_response",
        message: "La respuesta del servidor no es JSON válido.",
        status: response.status,
        requestId: responseId,
      });
    }
    return parseEnvelope<T>(body, response.status, responseId);
  }

  return {
    baseUrl,
    get: (path, options) => request(path, { method: "GET", signal: options?.signal ?? null }),
    postForm: (path, form, options) =>
      request(path, { method: "POST", body: form, signal: options?.signal ?? null }),
  };
}
