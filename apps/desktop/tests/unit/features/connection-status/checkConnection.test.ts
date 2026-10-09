import { describe, expect, it } from "vitest";

import { checkConnection } from "@/features/connection-status";

import {
  createFakeBackend,
  envelope,
  errorEnvelope,
  healthyRoutes,
  networkFailure,
} from "../../../support/fakeBackend";

describe("checkConnection", () => {
  it("reporta conectado cuando live y ready responden", async () => {
    const { client } = createFakeBackend(healthyRoutes);
    await expect(checkConnection(client)).resolves.toEqual({ status: "connected" });
  });

  it("atribuye la falla al servidor cuando no hay respuesta", async () => {
    const { client, calls } = createFakeBackend({ "GET /api/v1/health/live": networkFailure });
    await expect(checkConnection(client)).resolves.toMatchObject({
      status: "unavailable",
      component: "server",
    });
    expect(calls).toEqual(["GET /api/v1/health/live"]);
  });

  it("atribuye la falla a las dependencias cuando ready falla", async () => {
    const { client } = createFakeBackend({
      "GET /api/v1/health/live": () => envelope({ status: "ok" }),
      "GET /api/v1/health/ready": () =>
        errorEnvelope("internal_error", "Ocurrió un error interno", 500),
    });
    await expect(checkConnection(client)).resolves.toEqual({
      status: "unavailable",
      component: "dependencies",
      detail: "Ocurrió un error interno",
    });
  });
});
