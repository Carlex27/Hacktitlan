import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { App } from "@/app";
import type { DocumentReviewQueueItemDto } from "@/lib/api";

import {
  createFakeBackend,
  createFakeCertificate,
  envelope,
  errorEnvelope,
  healthyRoutes,
  type RouteHandler,
} from "../support/fakeBackend";

function item(overrides: Partial<DocumentReviewQueueItemDto>): DocumentReviewQueueItemDto {
  return {
    revision_number: 1,
    active_job_id: null,
    can_reprocess: true,
    certificate_id: 42,
    document_id: 10,
    source_file_name: null,
    certificate_no: "CM-42",
    manufacturer: "Fabricante Uno",
    uploaded_at: "2026-10-08T00:00:00+00:00",
    document_status: "needs_review",
    approval_status: "needs_review",
    quality_score: 0.7,
    blocking_issues_count: 1,
    warning_issues_count: 0,
    issues_summary: [
      {
        code: "missing_thickness",
        category: "missing",
        severity: "blocking",
        field_path: "products[0].thickness_mm",
        message: "Falta el espesor",
      },
    ],
    ...overrides,
  };
}

function renderWith(routes: Record<string, RouteHandler>) {
  const backend = createFakeBackend({ ...healthyRoutes, ...routes });
  render(<App apiClient={backend.client} />);
  return { backend, user: userEvent.setup() };
}

function queue() {
  return screen.findByRole("list", { name: "Revisión documental" });
}

describe("Revisión documental", () => {
  it("identifica los Excel por su nombre original durante procesamiento y revisión", async () => {
    renderWith({
      "GET /api/v1/document-reviews": () => envelope([
        item({ source_file_name: "MOLINOS GENERAL.xlsx", certificate_no: null }),
        item({ certificate_id: 43, source_file_name: "Otro molino.XLSX", active_job_id: 9, can_reprocess: false }),
      ]),
    });
    const list = await queue();
    expect(within(list).getByRole("listitem", { name: "MOLINOS GENERAL.xlsx" })).toBeInTheDocument();
    expect(within(list).getByRole("listitem", { name: "Otro molino.XLSX" })).toBeInTheDocument();
    expect(within(list).queryByText("Acta #42")).not.toBeInTheDocument();
  });
  it("muestra el resumen y los trabajos activos sin acciones de reprocesamiento", async () => {
    renderWith({
      "GET /api/v1/document-reviews": () =>
        envelope([
          item({}),
          item({ certificate_id: 43, certificate_no: "CM-43", active_job_id: 9, can_reprocess: false }),
          item({ certificate_id: 44, certificate_no: "CM-44", blocking_issues_count: 0, warning_issues_count: 0, issues_summary: [] }),
          item({ certificate_id: 45, certificate_no: "CM-45", blocking_issues_count: 0, warning_issues_count: 1 }),
        ]),
    });

    const list = await queue();
    expect(screen.queryByRole("region", { name: "Visor de documento" })).not.toBeInTheDocument();
    const ready = within(list).getByRole("listitem", { name: "CM-42" });
    expect(within(ready).queryByText(/Falta el espesor/)).not.toBeInTheDocument();
    expect(within(ready).queryByText("products[0].thickness_mm")).not.toBeInTheDocument();
    expect(within(ready).queryByRole("button", { name: "Volver a analizar" })).not.toBeInTheDocument();
    expect(within(ready).queryByRole("button", { name: "Reprocesar PDF" })).not.toBeInTheDocument();
    expect(within(ready).queryByLabelText("Persona responsable")).not.toBeInTheDocument();
    expect(within(ready).queryByLabelText("Motivo del reprocesamiento")).not.toBeInTheDocument();

    const busy = within(list).getByRole("listitem", { name: "CM-43" });
    expect(within(busy).getByText(/trabajo #9/)).toBeInTheDocument();
    expect(within(busy).queryByRole("button", { name: "Volver a analizar" })).not.toBeInTheDocument();
    for (const name of ["CM-44", "CM-45"]) {
      expect(within(within(list).getByRole("listitem", { name })).queryByRole("button", { name: "Volver a analizar" })).not.toBeInTheDocument();
    }
    expect(within(busy).queryByRole("button", { name: "Reprocesar PDF" })).not.toBeInTheDocument();
  });

  it("actualiza la cola sin enviar solicitudes de reprocesamiento", async () => {
    const { backend, user } = renderWith({
      "GET /api/v1/document-reviews": () => envelope([item({})]),
    });
    await queue();
    await user.click(screen.getByRole("button", { name: "Actualizar revisiones" }));
    await waitFor(() => expect(backend.calls.filter((call) => call === "GET /api/v1/document-reviews")).toHaveLength(2));
    expect(backend.calls.some((call) => call.includes("/reprocess"))).toBe(false);
  });

  it("muestra el error con reintento y abre el acta en Validación", async () => {
    let calls = 0;
    const { user } = renderWith({
      "GET /api/v1/document-reviews": () => {
        calls += 1;
        return calls === 1
          ? errorEnvelope("internal_error", "Ocurrió un error interno", 500)
          : envelope([item({})]);
      },
      "GET /api/v1/certificates/42": () =>
        envelope(createFakeCertificate({ id: 42, manufacturer: "Fabricante Uno" })),
      "GET /api/v1/certificates/42/classification-runs": () => envelope([]),
    });

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("No se pudieron cargar las revisiones");
    await user.click(within(alert).getByRole("button", { name: "Reintentar" }));

    const row = within(await queue()).getByRole("listitem", { name: "CM-42" });
    await user.click(within(row).getByRole("button", { name: "Revisar" }));
    expect(await screen.findByText("Fabricante Uno")).toBeInTheDocument();
  });

  it("indica cuando no hay revisiones pendientes", async () => {
    renderWith({});
    expect(await screen.findByText("No hay revisiones pendientes")).toBeInTheDocument();
  });
});
