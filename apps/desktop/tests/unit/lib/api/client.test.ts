import { describe, expect, it, vi } from "vitest";

import { ApiError, createApiClient, parseEnvelope, resolveApiBaseUrl } from "@/lib/api";

import { envelope, errorEnvelope } from "../../../support/fakeBackend";

describe("resolveApiBaseUrl", () => {
  it("usa el valor por defecto cuando no hay configuración", () => {
    expect(resolveApiBaseUrl(undefined)).toBe("http://127.0.0.1:8765");
    expect(resolveApiBaseUrl("   ")).toBe("http://127.0.0.1:8765");
  });

  it("elimina barras finales", () => {
    expect(resolveApiBaseUrl("http://servidor.ts.net:8765//")).toBe("http://servidor.ts.net:8765");
  });
});

describe("parseEnvelope", () => {
  it("devuelve data y meta en respuestas correctas", () => {
    const result = parseEnvelope<{ id: number }>(
      { data: { id: 1 }, meta: { limit: 50 }, error: null },
      200,
      "r",
    );
    expect(result).toEqual({ data: { id: 1 }, meta: { limit: 50 } });
  });

  it("conserva data nula sin convertirla", () => {
    expect(parseEnvelope({ data: null, meta: {}, error: null }, 200, "r").data).toBeNull();
  });

  it("convierte el sobre de error en ApiError de servidor", () => {
    const parse = () =>
      parseEnvelope(
        { data: null, meta: {}, error: { code: "not_found", message: "No existe", details: { id: 3 } } },
        404,
        "r",
      );
    expect(parse).toThrow(ApiError);
    try {
      parse();
    } catch (error) {
      expect(error).toMatchObject({
        kind: "server",
        code: "not_found",
        message: "No existe",
        status: 404,
        details: { id: 3 },
        requestId: "r",
      });
    }
  });

  it("rechaza cuerpos fuera de contrato", () => {
    expect(() => parseEnvelope({ detail: "x" }, 500, "r")).toThrow(
      expect.objectContaining({ kind: "invalid_response" }),
    );
    expect(() => parseEnvelope({ data: 1, error: null }, 500, "r")).toThrow(
      expect.objectContaining({ kind: "invalid_response" }),
    );
  });
});

describe("createApiClient", () => {
  it("reutiliza respuestas sólo con TTL explícito, las aísla y permite forzar recarga", async () => {
    const fetch = vi.fn(async () => envelope({ id: 1 }));
    const client = createApiClient({ baseUrl: "http://api", fetch });
    const first = await client.get<{ id: number }>("/detail", { cacheTtlMs: 5000 });
    first.data.id = 99;
    expect((await client.get<{ id: number }>("/detail", { cacheTtlMs: 5000 })).data.id).toBe(1);
    expect(fetch).toHaveBeenCalledTimes(1);
    await client.get("/detail", { cacheTtlMs: 0 });
    await client.get("/jobs/1");
    await client.get("/jobs/1");
    expect(fetch).toHaveBeenCalledTimes(4);
  });

  it("expira la caché y respeta la cancelación incluso en un acierto", async () => {
    const now = vi.spyOn(Date, "now");
    try {
      now.mockReturnValue(1000);
      const fetch = vi.fn(async () => envelope(1));
      const client = createApiClient({ baseUrl: "http://api", fetch });
      await client.get("/detail", { cacheTtlMs: 5000 });
      const controller = new AbortController();
      controller.abort();
      await expect(client.get("/detail", { cacheTtlMs: 5000, signal: controller.signal })).rejects.toMatchObject({ kind: "aborted" });
      now.mockReturnValue(6000);
      await client.get("/detail", { cacheTtlMs: 5000 });
      expect(fetch).toHaveBeenCalledTimes(2);
    } finally {
      now.mockRestore();
    }
  });

  it.each(["post", "patch", "delete", "postForm"] as const)("invalida las lecturas después de %s", async (method) => {
    const fetch = vi.fn(async () => envelope(1));
    const client = createApiClient({ baseUrl: "http://api", fetch });
    await client.get("/detail", { cacheTtlMs: 5000 });
    if (method === "delete") await client.delete("/write");
    else if (method === "postForm") await client.postForm("/write", new FormData());
    else await client[method]("/write", {});
    await client.get("/detail", { cacheTtlMs: 5000 });
    expect(fetch).toHaveBeenCalledTimes(3);
  });

  it("no conserva errores ni lecturas iniciadas antes de una escritura", async () => {
    let finish: (response: Response) => void = () => {};
    const fetch = vi.fn(async (_url: string, init?: RequestInit) => {
      if (init?.method !== "GET") return envelope(2);
      return new Promise<Response>((resolve) => { finish = resolve; });
    });
    const client = createApiClient({ baseUrl: "http://api", fetch });
    const pending = client.get("/detail", { cacheTtlMs: 5000 });
    await client.post("/write", {});
    finish(envelope(1));
    await pending;
    const retry = client.get("/detail", { cacheTtlMs: 5000 });
    finish(errorEnvelope("unavailable", "Error", 503));
    await expect(retry).rejects.toMatchObject({ kind: "server" });
    const recovered = client.get("/detail", { cacheTtlMs: 5000 });
    finish(envelope(2));
    await expect(recovered).resolves.toMatchObject({ data: 2 });
    expect(fetch).toHaveBeenCalledTimes(4);
  });

  it("envía X-Request-ID y combina la URL base", async () => {
    let seenUrl = "";
    let seenId: string | null = null;
    const client = createApiClient({
      baseUrl: "http://api",
      createRequestId: () => "abc",
      fetch: async (input, init) => {
        seenUrl = input;
        seenId = new Headers(init?.headers).get("X-Request-ID");
        return envelope({ status: "ok" });
      },
    });
    await expect(client.get("/api/v1/health/live")).resolves.toMatchObject({ data: { status: "ok" } });
    expect(seenUrl).toBe("http://api/api/v1/health/live");
    expect(seenId).toBe("abc");
  });

  it("clasifica fallas de red", async () => {
    const client = createApiClient({
      baseUrl: "http://api",
      fetch: async () => {
        throw new TypeError("Failed to fetch");
      },
    });
    await expect(client.get("/x")).rejects.toMatchObject({ kind: "network" });
  });

  it("distingue cancelaciones de fallas de red", async () => {
    const controller = new AbortController();
    controller.abort();
    const client = createApiClient({
      baseUrl: "http://api",
      fetch: async () => {
        throw new DOMException("Aborted", "AbortError");
      },
    });
    await expect(client.get("/x", { signal: controller.signal })).rejects.toMatchObject({
      kind: "aborted",
    });
  });

  it("propaga errores del servidor y respuestas no JSON", async () => {
    const failing = createApiClient({
      baseUrl: "http://api",
      fetch: async () => errorEnvelope("internal_error", "Ocurrió un error interno", 500),
    });
    await expect(failing.get("/x")).rejects.toMatchObject({ kind: "server", code: "internal_error" });

    const html = createApiClient({
      baseUrl: "http://api",
      fetch: async () => new Response("<html>", { status: 502 }),
    });
    await expect(html.get("/x")).rejects.toMatchObject({ kind: "invalid_response", status: 502 });
  });
});
