import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { AppProviders } from "@/app/providers/AppProviders";
import { ApprovalBar } from "@/features/classification-results";
import { es } from "@/lib/i18n";
import {
  createFakeBackend,
  createFakeCertificate,
  createFakeClassificationRun,
  envelope,
  errorEnvelope,
} from "../../../support/fakeBackend";

describe("ApprovalBar", () => {
  it("bloquea el acta hasta autorizar todos sus rollos y se habilita tras recargar", async () => {
    const user = userEvent.setup();
    const backend = createFakeBackend();
    const certificate = createFakeCertificate();
    const run = createFakeClassificationRun();
    const pendingRun = { ...run, results: run.results.map((result) => ({ ...result, current_selection: null })) };
    const { rerender } = render(<AppProviders apiClient={backend.client}><ApprovalBar run={pendingRun} certificate={certificate} /></AppProviders>);
    const button = screen.getByRole("button", { name: /confirmar acta/i });
    expect(button).toBeDisabled();
    expect(screen.getByText(/Coladas pendientes: C-9876/)).toBeInTheDocument();
    expect(screen.getByText(/Selecciones pendientes: PL-001/)).toBeInTheDocument();
    await user.click(button);
    expect(backend.calls).toHaveLength(0);
    rerender(<AppProviders apiClient={backend.client}><ApprovalBar run={run} certificate={certificate} /></AppProviders>);
    expect(button).toBeEnabled();
    rerender(<AppProviders apiClient={backend.client}><ApprovalBar run={run} certificate={certificate} isLoading /></AppProviders>);
    expect(button).toBeDisabled();
    expect(screen.getByText(es.approval.coverageLoading)).toBeInTheDocument();
    rerender(<AppProviders apiClient={backend.client}><ApprovalBar run={run} certificate={certificate} loadError={new Error("Sin conexión")} /></AppProviders>);
    expect(button).toBeDisabled();
    expect(screen.getByText(es.approval.coverageUnavailable)).toBeInTheDocument();
  });
  it.each(["approve", "reject"])("envía %s con auditoría fija y sin campos de captura", async (action) => {
    const user = userEvent.setup();
    let body: unknown;
    const backend = createFakeBackend({
      [`POST /api/v1/classification-runs/101/${action}`]: (init) => {
        body = JSON.parse(String(init?.body));
        return envelope({ classification_run_id: 101, approval_status: "draft" });
      },
    });
    const onDecisionComplete = vi.fn();
    render(<AppProviders apiClient={backend.client}><ApprovalBar run={createFakeClassificationRun()} certificate={createFakeCertificate()} onDecisionComplete={onDecisionComplete} /></AppProviders>);
    expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Guardar borrador" })).not.toBeInTheDocument();
    const label = action === "approve" ? "Confirmar acta" : "Rechazar";
    await user.click(screen.getByRole("button", { name: label }));
    await waitFor(() => expect(onDecisionComplete).toHaveBeenCalled());
    expect(body).toEqual({ person_name: es.approval.defaultPerson, reason: es.approval.defaultReason });
  });
  it("muestra el error del servidor sin ocultarlo", async () => {
    const backend = createFakeBackend({ "POST /api/v1/classification-runs/101/approve": () => errorEnvelope("missing_fraction", "Falta fracción", 400) });
    render(<AppProviders apiClient={backend.client}><ApprovalBar run={createFakeClassificationRun()} certificate={createFakeCertificate()} /></AppProviders>);
    await userEvent.setup().click(screen.getByRole("button", { name: "Confirmar acta" }));
    expect(await screen.findByText("Falta fracción")).toBeInTheDocument();
  });
});

it("explica carga, ausencia de clasificación y error sin mostrar un dictamen vacío", () => {
  const backend = createFakeBackend();
  const { rerender } = render(<AppProviders apiClient={backend.client}><ApprovalBar run={null} certificate={null} isLoading /></AppProviders>);
  expect(screen.getByRole("status")).toHaveTextContent(es.approval.coverageLoading);
  rerender(<AppProviders apiClient={backend.client}><ApprovalBar run={null} certificate={null} /></AppProviders>);
  expect(screen.getByRole("status")).toHaveTextContent(es.classification.noRunsTitle);
  rerender(<AppProviders apiClient={backend.client}><ApprovalBar run={null} certificate={null} loadError={new Error("Fallo de conexión")} /></AppProviders>);
  expect(screen.getByRole("alert")).toHaveTextContent(es.classification.loadError);
});
