import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it } from "vitest";
import { AppProviders } from "@/app/providers/AppProviders";
import { ValidationPage } from "@/pages";
import { createFakeBackend, createFakeCertificate, createFakeClassificationRun, envelope } from "../support/fakeBackend";

it("bloquea sugerencias y captura manual después de confirmar el acta", async () => {
  let run = createFakeClassificationRun();
  const backend = createFakeBackend({
    "GET /api/v1/certificates/42": () => envelope(createFakeCertificate()),
    "GET /api/v1/certificates/42/classification-runs": () => envelope([{ id: 101 }]),
    "GET /api/v1/classification-runs/101": () => envelope(run),
    "POST /api/v1/classification-runs/101/approve": () => {
      run = { ...run, approval_status: "approved" };
      return envelope({ classification_run_id: 101, approval_status: "approved" });
    },
  });
  const user = userEvent.setup();
  render(<AppProviders apiClient={backend.client}><ValidationPage certificateId={42} documentId={10} /></AppProviders>);
  await user.click(screen.getByRole("button", { name: "Validación" }));
  expect(await screen.findByRole("button", { name: "Elegir fracción" })).toBeEnabled();
  await user.click(screen.getByRole("button", { name: "Dictamen de clasificación" }));
  await user.click(await screen.findByRole("button", { name: "Confirmar acta" }));
  await waitFor(() => expect(backend.calls).toContain("POST /api/v1/classification-runs/101/approve"));
  await user.click(screen.getByRole("button", { name: "Validación" }));
  await waitFor(() => expect(screen.getByRole("button", { name: "Elegir fracción" })).toBeDisabled());
  for (const radio of screen.getAllByRole("radio")) expect(radio).toBeDisabled();
  expect(screen.getByLabelText("Fracción arancelaria (8 dígitos)")).toBeDisabled();
  expect(screen.getByLabelText("NICO (2 dígitos)")).toBeDisabled();
  await user.click(screen.getByRole("button", { name: "Elegir fracción" }));
  expect(backend.calls.some((call) => call.endsWith("/select"))).toBe(false);
});

it.each([true, false])("la página sólo permite confirmar cuando todas las coladas están autorizadas: %s", async (complete) => {
  const certificate = createFakeCertificate();
  const authorized = createFakeClassificationRun();
  const run = complete ? authorized : { ...authorized, results: authorized.results.map((result) => ({ ...result, current_selection: null })) };
  const backend = createFakeBackend({
    "GET /api/v1/certificates/42": () => envelope(certificate),
    "GET /api/v1/certificates/42/classification-runs": () => envelope([{ id: 101 }]),
    "GET /api/v1/classification-runs/101": () => envelope(run),
  });
  render(<AppProviders apiClient={backend.client}><ValidationPage certificateId={42} documentId={10} /></AppProviders>);
  await userEvent.setup().click(screen.getByRole("button", { name: "Dictamen de clasificación" }));
  const confirm = await screen.findByRole("button", { name: /confirmar acta/i });
  await waitFor(() => complete ? expect(confirm).toBeEnabled() : expect(screen.getByText(/Coladas pendientes: C-9876/)).toBeInTheDocument());
  if (complete) expect(confirm).toBeEnabled();
  else expect(confirm).toBeDisabled();
  expect(backend.calls.some((call) => call.endsWith("/approve"))).toBe(false);
});

it("permite cerrar el acta revisada por un humano aunque el motor conserve datos faltantes", async () => {
  const run = createFakeClassificationRun();
  run.results = run.results.map((result) => ({ ...result, candidates: result.candidates.map((candidate) => ({ ...candidate,
    details: { missing_fields: ["composition_pct.Cr", "nico_qualifier"] },
  })) }));
  const backend = createFakeBackend({
    "GET /api/v1/certificates/42": () => envelope(createFakeCertificate()),
    "GET /api/v1/certificates/42/classification-runs": () => envelope([{ id: 101 }]),
    "GET /api/v1/classification-runs/101": () => envelope(run),
  });
  render(<AppProviders apiClient={backend.client}><ValidationPage certificateId={42} documentId={10} /></AppProviders>);
  await userEvent.setup().click(screen.getByRole("button", { name: "Dictamen de clasificación" }));
  await screen.findByText(/Puedes confirmar el acta/);
  expect(screen.getByRole("button", { name: "Confirmar acta" })).toBeEnabled();
  expect(backend.calls.some((call) => call.endsWith("/approve"))).toBe(false);
});
