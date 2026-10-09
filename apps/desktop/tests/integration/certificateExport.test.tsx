import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { App } from "@/app";
import { createFakeBackend, createFakeCertificate, envelope, errorEnvelope, healthyRoutes } from "../support/fakeBackend";

function backendForExport() {
  return createFakeBackend({ ...healthyRoutes,
    "GET /api/v1/certificates": () => envelope([createFakeCertificate()]),
    "GET /api/v1/certificates/42": () => envelope(createFakeCertificate()),
    "GET /api/v1/certificates/42/classification-runs": () => envelope([]),
    "POST /api/v1/exports": (init) => {
      expect(JSON.parse(String(init?.body))).toEqual({ certificate_ids: [42], official: false, person_name: "Administrador" });
      return envelope({ export_id: 7, job_id: 8 }, 202);
    },
    "GET /api/v1/exports/7": () => envelope({ status: "succeeded", download_url: "/api/v1/exports/7/file" }),
  });
}

describe("Exportación del acta completa", () => {
  it("anuncia la espera e impide duplicar solicitudes durante el procesamiento", async () => {
    const backend = backendForExport();
    backend.routes.set("GET /api/v1/exports/7", () => envelope({ status: "queued", download_url: null }));
    const user = userEvent.setup();
    render(<App apiClient={backend.client} />);
    await user.click(await screen.findByRole("button", { name: "Historial de actas" }));
    await user.click(await screen.findByRole("button", { name: "Abrir acta" }));
    await waitFor(() => expect(screen.getByRole("button", { name: "Generar Excel" })).toBeEnabled());
    await user.click(screen.getByRole("button", { name: "Generar Excel" }));
    expect(await screen.findByRole("button", { name: "Generando Excel…" })).toBeDisabled();
    await user.click(screen.getByRole("button", { name: "Generando Excel…" }));
    expect(backend.calls.filter(call => call === "POST /api/v1/exports")).toHaveLength(1);
    expect(screen.queryByRole("link", { name: "Descargar Excel" })).not.toBeInTheDocument();
    backend.routes.set("GET /api/v1/exports/7", () => envelope({ status: "succeeded", download_url: "/api/v1/exports/7/file" }));
    expect(await screen.findByRole("link", { name: "Descargar Excel" }, { timeout: 3000 })).toBeVisible();
  });
  it("genera el reporte de un acta pendiente sin clasificación y ofrece su descarga", async () => {
    const backend = backendForExport();
    const user = userEvent.setup();
    render(<App apiClient={backend.client} />);
    await user.click(await screen.findByRole("button", { name: "Historial de actas" }));
    await user.click(await screen.findByRole("button", { name: "Abrir acta" }));
    await waitFor(() => expect(screen.getByRole("button", { name: "Generar Excel" })).toBeEnabled());
    await user.click(screen.getByRole("button", { name: "Generar Excel" }));
    expect(await screen.findByRole("link", { name: "Descargar Excel" })).toHaveAttribute("href", "http://backend.test/api/v1/exports/7/file");
    expect(backend.calls.filter(call => call === "POST /api/v1/exports")).toHaveLength(1);
  });

  it("muestra el error del worker y permite generar de nuevo", async () => {
    const backend = backendForExport();
    backend.routes.set("GET /api/v1/exports/7", () => envelope({ status: "failed", error_message: "Archivo no disponible" }));
    const user = userEvent.setup();
    render(<App apiClient={backend.client} />);
    await user.click(await screen.findByRole("button", { name: "Historial de actas" }));
    await user.click(await screen.findByRole("button", { name: "Abrir acta" }));
    await waitFor(() => expect(screen.getByRole("button", { name: "Generar Excel" })).toBeEnabled());
    await user.click(screen.getByRole("button", { name: "Generar Excel" }));
    expect(await screen.findByText("Archivo no disponible")).toBeVisible();
    expect(screen.queryByRole("link", { name: "Descargar Excel" })).not.toBeInTheDocument();
    backend.routes.set("POST /api/v1/exports", () => errorEnvelope("unavailable", "Intente más tarde", 503));
    await user.click(screen.getByRole("button", { name: "Generar Excel" }));
    expect(await screen.findByText("Intente más tarde")).toBeVisible();
  });
});
