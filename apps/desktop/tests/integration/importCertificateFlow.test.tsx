import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { App } from "@/app";
import type { JobDto } from "@/lib/api";

import {
  createFakeBackend,
  envelope,
  errorEnvelope,
  healthyRoutes,
  networkFailure,
  pdfFile,
} from "../support/fakeBackend";

function jobResponse(status: JobDto["status"], progress: number | null, error_message: string | null = null) {
  return envelope({
    id: 11,
    document_id: 5,
    kind: "extract_document",
    status,
    progress,
    attempts: 1,
    max_attempts: 3,
    error_code: null,
    error_message,
    result: null,
  } satisfies JobDto);
}

describe("Importación de actas", () => {
  it("bloquea sin servidor y permite reintentar", async () => {
    const user = userEvent.setup();
    const backend = createFakeBackend({ "GET /api/v1/health/live": networkFailure });
    render(<App apiClient={backend.client} />);

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("No se puede contactar al servidor");
    expect(alert).toHaveTextContent("http://backend.test");
    expect(screen.queryByLabelText(/seleccionar certificados pdf/i)).not.toBeInTheDocument();

    for (const [key, handler] of Object.entries(healthyRoutes)) backend.routes.set(key, handler);
    await user.click(within(alert).getByRole("button", { name: /reintentar/i }));

    expect(await screen.findByLabelText(/seleccionar certificados pdf/i)).toBeInTheDocument();
  });

  it("indica cuando PostgreSQL o el almacenamiento no están listos", async () => {
    const backend = createFakeBackend({
      ...healthyRoutes,
      "GET /api/v1/health/ready": () => errorEnvelope("internal_error", "Ocurrió un error interno", 500),
    });
    render(<App apiClient={backend.client} />);
    expect(await screen.findByRole("alert")).toHaveTextContent("El servidor no está listo");
  });

  it.each(["succeeded", "needs_review"] as const)("retira el PDF de la cola al terminar en %s", async (status) => {
    const user = userEvent.setup();
    const jobs = [jobResponse("queued", 0), jobResponse("running", 50), jobResponse(status, 100)];
    const backend = createFakeBackend({
      ...healthyRoutes,
      "POST /api/v1/documents": () =>
        envelope({ document_id: 5, certificate_id: 21, job_id: 11, duplicate: false }, 202),
      "GET /api/v1/jobs/11": () => jobs.shift() ?? jobResponse(status, 100),
    });
    render(<App apiClient={backend.client} />);

    expect(await screen.findByText("No hay archivos seleccionados")).toBeInTheDocument();
    await user.upload(screen.getByLabelText(/seleccionar certificados pdf/i), pdfFile("molino-1.pdf"));

    const row = (await screen.findByText("molino-1.pdf")).closest("li");
    expect(row).not.toBeNull();
    await waitFor(() => expect(row).not.toBeInTheDocument(), { timeout: 8000 });
    expect(screen.getByText("No hay archivos seleccionados")).toBeInTheDocument();
    expect(backend.calls.filter((call) => call === "GET /api/v1/jobs/11")).toHaveLength(3);
  }, 10_000);

  it("muestra el error del servidor cuando la carga se rechaza", async () => {
    const user = userEvent.setup();
    const backend = createFakeBackend({
      ...healthyRoutes,
      "POST /api/v1/documents": () =>
        errorEnvelope("file_too_large", "El PDF excede el tamaño máximo permitido", 413),
    });
    render(<App apiClient={backend.client} />);

    await user.upload(await screen.findByLabelText(/seleccionar certificados pdf/i), pdfFile("grande.pdf"));

    const row = (await screen.findByText("grande.pdf")).closest("li");
    await waitFor(() => expect(row).toHaveAttribute("data-status", "error"));
    expect(row).toHaveTextContent("El PDF excede el tamaño máximo permitido");
  });

  it("marca revisión cuando el PDF requiere OCR", async () => {
    const user = userEvent.setup();
    const backend = createFakeBackend({
      ...healthyRoutes,
      "POST /api/v1/documents": () =>
        envelope({ document_id: 5, certificate_id: 21, job_id: 11, duplicate: true }, 200),
      "GET /api/v1/jobs/11": () => jobResponse("needs_ocr", 100),
    });
    render(<App apiClient={backend.client} />);

    await user.upload(await screen.findByLabelText(/seleccionar certificados pdf/i), pdfFile("escaneado.pdf"));

    const row = (await screen.findByText("escaneado.pdf")).closest("li");
    await waitFor(() => expect(row).toHaveAttribute("data-status", "needs_review"));
    expect(row).toHaveTextContent("requiere OCR");
    expect(row).toHaveTextContent("Archivo ya registrado previamente");
  });
});
