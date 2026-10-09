import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { AppProviders } from "@/app/providers/AppProviders";
import { ApprovalBar } from "@/features/classification-results";
import { es } from "@/lib/i18n";
import {
  createFakeBackend,
  createFakeClassificationRun,
  envelope,
  errorEnvelope,
} from "../../../support/fakeBackend";

describe("ApprovalBar", () => {
  it("valida persona y motivo obligatorios antes de enviar aprobación", async () => {
    const user = userEvent.setup();
    const backend = createFakeBackend();
    const run = createFakeClassificationRun();

    render(
      <AppProviders apiClient={backend.client}>
        <ApprovalBar run={run} />
      </AppProviders>,
    );

    const approveButton = screen.getByRole("button", { name: /aprobar/i });
    await user.click(approveButton);

    expect(screen.getByText(es.approval.personRequired)).toBeInTheDocument();
    expect(screen.getByText(es.approval.reasonRequired)).toBeInTheDocument();
    expect(backend.calls).toHaveLength(0);
  });

  it("envía aprobación con persona y motivo correctos", async () => {
    const user = userEvent.setup();
    const onDecisionComplete = vi.fn();
    const backend = createFakeBackend({
      "POST /api/v1/classification-runs/101/approve": () =>
        envelope({ classification_run_id: 101, approval_status: "approved" }),
    });
    const run = createFakeClassificationRun({ id: 101 });

    render(
      <AppProviders apiClient={backend.client}>
        <ApprovalBar run={run} onDecisionComplete={onDecisionComplete} />
      </AppProviders>,
    );

    const personInput = screen.getByPlaceholderText(es.approval.personPlaceholder);
    const reasonInput = screen.getByPlaceholderText(es.approval.reasonPlaceholder);

    await user.type(personInput, "Ing. Carlos Mendoza");
    await user.type(reasonInput, "Conforme a norma técnica EN 10025");

    const approveButton = screen.getByRole("button", { name: /aprobar/i });
    await user.click(approveButton);

    await waitFor(() => {
      expect(backend.calls).toContain("POST /api/v1/classification-runs/101/approve");
    });
    expect(onDecisionComplete).toHaveBeenCalled();
  });

  it("muestra error del servidor cuando la aprobación es rechazada por el backend", async () => {
    const user = userEvent.setup();
    const backend = createFakeBackend({
      "POST /api/v1/classification-runs/101/approve": () =>
        errorEnvelope("missing_fraction", "No se puede aprobar sin fracción arancelaria asignada", 400),
    });
    const run = createFakeClassificationRun({ id: 101 });

    render(
      <AppProviders apiClient={backend.client}>
        <ApprovalBar run={run} />
      </AppProviders>,
    );

    await user.type(screen.getByPlaceholderText(es.approval.personPlaceholder), "Carlos");
    await user.type(screen.getByPlaceholderText(es.approval.reasonPlaceholder), "Revisión final");
    await user.click(screen.getByRole("button", { name: /aprobar/i }));

    expect(
      await screen.findByText("No se puede aprobar sin fracción arancelaria asignada"),
    ).toBeInTheDocument();
  });
});
