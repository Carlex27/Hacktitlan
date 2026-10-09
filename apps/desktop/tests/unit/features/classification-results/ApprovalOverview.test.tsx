import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";
import { AppProviders } from "@/app/providers/AppProviders";
import { ApprovalBar } from "@/features/classification-results";
import { es } from "@/lib/i18n";
import { createFakeBackend, createFakeCertificate, createFakeClassificationRun } from "../../../support/fakeBackend";

it("presenta el cierre confirmado y conserva sólo la acción disponible", () => {
  render(<AppProviders apiClient={createFakeBackend().client}><ApprovalBar certificate={createFakeCertificate()} run={createFakeClassificationRun({ approval_status: "approved" })} /></AppProviders>);
  expect(screen.getByText(es.approval.approvedExplanation)).toBeVisible();
  expect(screen.queryByText(/Rollos/)).not.toBeInTheDocument();
  expect(screen.getByText(es.approval.reviewedHeats)).toBeVisible();
  expect(screen.queryByRole("button", { name: "Confirmar acta" })).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Guardar borrador" })).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Rechazar" })).toBeEnabled();
});
