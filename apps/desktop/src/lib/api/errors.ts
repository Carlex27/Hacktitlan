export type ApiErrorKind =
  /** El servidor no respondió: backend apagado, Tailscale caído o red. */
  | "network"
  /** El servidor respondió con un error en el sobre `error`. */
  | "server"
  /** La respuesta no cumple el contrato `{ data, meta, error }`. */
  | "invalid_response"
  /** La solicitud fue cancelada por la interfaz. */
  | "aborted";

export interface ApiErrorInit {
  kind: ApiErrorKind;
  message: string;
  code?: string | undefined;
  status?: number | undefined;
  details?: Readonly<Record<string, unknown>> | undefined;
  requestId?: string | undefined;
}

export class ApiError extends Error {
  readonly kind: ApiErrorKind;
  readonly code: string | undefined;
  readonly status: number | undefined;
  readonly details: Readonly<Record<string, unknown>>;
  readonly requestId: string | undefined;

  constructor(init: ApiErrorInit) {
    super(init.message);
    this.name = "ApiError";
    this.kind = init.kind;
    this.code = init.code;
    this.status = init.status;
    this.details = init.details ?? {};
    this.requestId = init.requestId;
  }
}

export function isAbortError(error: unknown): boolean {
  return (
    (error instanceof ApiError && error.kind === "aborted") ||
    (error instanceof DOMException && error.name === "AbortError")
  );
}
