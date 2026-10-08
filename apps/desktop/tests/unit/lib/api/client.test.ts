import { describe, expect, it } from "vitest";

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
