import { createApiClient, type ApiClient, type FetchLike } from "@/lib/api";

export type RouteHandler = (init: RequestInit | undefined) => Response | Promise<Response>;

export function envelope(data: unknown, status = 200): Response {
  return Response.json({ data, meta: {}, error: null }, { status });
}

export function errorEnvelope(code: string, message: string, status: number): Response {
  return Response.json({ data: null, meta: {}, error: { code, message, details: {} } }, { status });
}

export function networkFailure(): never {
  throw new TypeError("Failed to fetch");
}

export interface FakeBackend {
  client: ApiClient;
  /** Rutas `"METHOD /path"` → manejador; se pueden reemplazar durante la prueba. */
  routes: Map<string, RouteHandler>;
  calls: string[];
}

export const TEST_BASE_URL = "http://backend.test";

export function createFakeBackend(routes: Record<string, RouteHandler> = {}): FakeBackend {
  const table = new Map(Object.entries(routes));
  const calls: string[] = [];
  const fetchImpl: FetchLike = async (input, init) => {
    const key = `${init?.method ?? "GET"} ${input.replace(TEST_BASE_URL, "")}`;
    calls.push(key);
    const handler = table.get(key);
    if (!handler) throw new Error(`Ruta no simulada: ${key}`);
    return handler(init);
  };
  return {
    client: createApiClient({ baseUrl: TEST_BASE_URL, fetch: fetchImpl, createRequestId: () => "req-1" }),
    routes: table,
    calls,
  };
}

export const healthyRoutes: Record<string, RouteHandler> = {
  "GET /api/v1/health/live": () => envelope({ status: "ok" }),
  "GET /api/v1/health/ready": () =>
    envelope({ status: "ready", database: "available", storage: "available" }),
};

export function pdfFile(name = "molino-1.pdf"): File {
  return new File(["%PDF-1.7"], name, { type: "application/pdf" });
}
