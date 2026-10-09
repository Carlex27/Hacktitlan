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
  it("lista las actas con incidencias y bloquea el reprocesamiento con un trabajo activo", async () => {
    renderWith({
      "GET /api/v1/document-reviews": () =>
        envelope([
          item({}),
          item({ certificate_id: 43, certificate_no: "CM-43", active_job_id: 9, can_reprocess: false }),
        ]),
    });

    const list = await queue();
    const ready = within(list).getByRole("listitem", { name: "CM-42" });
    expect(within(ready).getByText(/Falta el espesor/)).toBeInTheDocument();
    expect(within(ready).getByRole("button", { name: "Reprocesar PDF" })).toBeEnabled();

    const busy = within(list).getByRole("listitem", { name: "CM-43" });
    expect(within(busy).getByText(/trabajo #9/)).toBeInTheDocument();
    expect(within(busy).getByRole("button", { name: "Reprocesar PDF" })).toBeDisabled();
  });

  it("reprocesa con persona y motivo, avisa la nueva revisión y actualiza la cola", async () => {
    let body: unknown;
    const { backend, user } = renderWith({
      "GET /api/v1/document-reviews": () => envelope([item({})]),
      "POST /api/v1/certificates/42/reprocess": (init) => {
        body = JSON.parse(String(init?.body));
        return envelope({
          certificate_id: 44,
          job_id: 12,
          stage: "extraction",
          status: "queued",
          quality_report: null,
        });
      },
    });

    const row = within(await queue()).getByRole("listitem", { name: "CM-42" });
    await user.click(within(row).getByRole("button", { name: "Reprocesar PDF" }));
    expect(within(row).getByLabelText("Persona responsable")).toHaveAttribute("aria-invalid", "true");
    expect(backend.calls).not.toContain("POST /api/v1/certificates/42/reprocess");

    await user.type(within(row).getByLabelText("Persona responsable"), "Ana López");
    await user.type(within(row).getByLabelText("Motivo del reprocesamiento"), "PDF corregido por el molino");
    await user.click(within(row).getByRole("button", { name: "Reprocesar PDF" }));

    expect(await screen.findByText(/la nueva revisión es el acta #44/)).toBeInTheDocument();
    expect(body).toEqual({
      from_stage: "extraction",
      person_name: "Ana López",
      reason: "PDF corregido por el molino",
    });
    await waitFor(() =>
      expect(backend.calls.filter((call) => call === "GET /api/v1/document-reviews")).toHaveLength(2),
    );
  });

  it("muestra el 409 de extracción en curso en la fila correspondiente", async () => {
    const { user } = renderWith({
      "GET /api/v1/document-reviews": () => envelope([item({})]),
      "POST /api/v1/certificates/42/reprocess": () =>
        errorEnvelope("reprocess_in_progress", "Este PDF ya tiene una extracción en curso", 409),
    });

    const row = within(await queue()).getByRole("listitem", { name: "CM-42" });
    await user.type(within(row).getByLabelText("Persona responsable"), "Ana López");
    await user.type(within(row).getByLabelText("Motivo del reprocesamiento"), "Reintento");
    await user.click(within(row).getByRole("button", { name: "Reprocesar PDF" }));

    const refreshedRow = within(await queue()).getByRole("listitem", { name: "CM-42" });
    expect(await within(refreshedRow).findByRole("alert")).toHaveTextContent(
      "Este PDF ya tiene una extracción en curso",
    );
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
