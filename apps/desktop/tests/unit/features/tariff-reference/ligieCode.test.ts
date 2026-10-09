import { describe, expect, it } from "vitest";

import { toLigieLookupCode } from "@/features/tariff-reference";

describe("toLigieLookupCode", () => {
  it("une fracción y NICO sin puntos ni guiones", () => {
    expect(toLigieLookupCode("7208.51.01", "00")).toBe("7208510100");
    expect(toLigieLookupCode("72085101", "00")).toBe("7208510100");
  });

  it("consulta sólo la fracción si falta el NICO", () => {
    expect(toLigieLookupCode("7208.51.01", null)).toBe("72085101");
  });

  it("sin fracción no hay referencia", () => {
    expect(toLigieLookupCode(null, "00")).toBeNull();
    expect(toLigieLookupCode("  ", null)).toBeNull();
  });
});

describe("isReferenceUnsupported", () => {
  it("distingue ruta inexistente de código inexistente", async () => {
    const { ApiError } = await import("@/lib/api");
    const { isReferenceUnsupported } = await import("@/features/tariff-reference");
    expect(isReferenceUnsupported(new ApiError({ kind: "server", code: "http_error", status: 404, message: "Not Found" }))).toBe(true);
    expect(isReferenceUnsupported(new ApiError({ kind: "server", code: "not_found", status: 404, message: "No existe" }))).toBe(false);
    expect(isReferenceUnsupported(new ApiError({ kind: "network", message: "Sin red" }))).toBe(false);
  });
});
