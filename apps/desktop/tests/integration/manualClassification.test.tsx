import { render, screen, within, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it } from "vitest";
import { AppProviders } from "@/app/providers/AppProviders";
import { ValidationPage } from "@/pages";
import { createFakeBackend, createFakeCertificate, createFakeClassificationRun, envelope, errorEnvelope } from "../support/fakeBackend";

it("retira la selección, actualiza el estado y permite sustituirla por códigos manuales", async () => {
  let run = createFakeClassificationRun();
  let fail = true;
  const backend = createFakeBackend({
    "GET /api/v1/certificates/42": () => envelope(createFakeCertificate()),
    "GET /api/v1/certificates/42/classification-runs": () => envelope([{ id: 101 }]),
    "GET /api/v1/classification-runs/101": () => envelope(run),
    "POST /api/v1/classification-results/201/deselect": () => {
      if (fail) return errorEnvelope("conflict", "No se pudo quitar la selección", 409);
      run = { ...run, results: run.results.map((result) => ({ ...result,
        current_selection: null, fraction: null, nico: null, outcome: "needs_review",
      })) };
      return envelope({ classification_result_id: 201, outcome: "needs_review" });
    },
  });
  const user = userEvent.setup();
  render(<AppProviders apiClient={backend.client}><ValidationPage certificateId={42} documentId={10} /></AppProviders>);
  await user.click(screen.getByRole("button", { name: "Validación" }));
  const remove = await screen.findByRole("button", { name: "Quitar selección de fracción y NICO" });
  expect(screen.getByLabelText("Fracción arancelaria (8 dígitos)")).toBeEnabled();
  expect(screen.getByLabelText("NICO (2 dígitos)")).toBeEnabled();
  await user.click(remove);
  expect(await screen.findByText("No se pudo quitar la selección")).toBeInTheDocument();
  expect(screen.getByText(/Clasificación autorizada:/)).toBeInTheDocument();
  fail = false;
  await user.click(remove);
  await waitFor(() => expect(screen.queryByRole("button", { name: "Quitar selección de fracción y NICO" })).not.toBeInTheDocument());
  expect(screen.queryByRole("button", { name: "Quitar selección de fracción y NICO" })).not.toBeInTheDocument();
  expect(screen.queryByText(/Clasificación autorizada:/)).not.toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Dictamen de clasificación" }));
  expect(await screen.findByRole("button", { name: "Confirmar acta" })).toBeDisabled();
});

it("guarda códigos manuales del rollo, muestra errores y recarga su selección sin perder sugerencias", async () => {
  let run = createFakeClassificationRun();
  let body: unknown;
  let fail = true;
  const backend = createFakeBackend({
    "GET /api/v1/certificates/42": () => envelope(createFakeCertificate()),
    "GET /api/v1/certificates/42/classification-runs": () => envelope([{ id: 101 }]),
    "GET /api/v1/classification-runs/101": () => envelope(run),
    "POST /api/v1/classification-results/201/select": (init) => {
      body = JSON.parse(String(init?.body));
      if (fail) return errorEnvelope("conflict", "Revisa la clasificación", 409);
      run = { ...run, results: run.results.map((result) => ({ ...result, fraction: "72091701", nico: "01",
        current_selection: { id: 501, candidate_id: 999, supersedes_selection_id: 401, person_name: "Administrador", reason: "Revisión documental", workstation_name: "W1", created_at: "2026-10-08T12:00:00Z" },
        candidates: [...result.candidates, { id: 999, rank: 3, fraction: "72091701", nico: "01", description: "Captura manual", support_level: "conditional", details: { manual: true }, factors: [], detail_url: "/api/v1/classification-candidates/999" }],
      })) };
      return envelope({ candidate_id: 999, fraction: "72091701", nico: "01" });
    },
  });
  const user = userEvent.setup();
  render(<AppProviders apiClient={backend.client}><ValidationPage certificateId={42} documentId={10} /></AppProviders>);
  await user.click(screen.getByRole("button", { name: "Validación" }));
  const form = within(await screen.findByRole("form", { name: "Captura manual de fracción y NICO" }));
  await user.type(form.getByLabelText("Fracción arancelaria (8 dígitos)"), "72091701");
  await user.type(form.getByLabelText("NICO (2 dígitos)"), "01");
  await user.type(form.getByLabelText("Justificación de la captura manual"), "Revisión documental");
  await user.click(form.getByRole("button", { name: "Guardar clasificación manual" }));
  expect(await form.findByRole("alert")).toHaveTextContent("Revisa la clasificación");
  fail = false;
  await user.click(form.getByRole("button", { name: "Guardar clasificación manual" }));
  expect(await screen.findByText("Clasificación autorizada: 72091701 · NICO 01")).toBeInTheDocument();
  expect(body).toEqual({ fraction: "72091701", nico: "01", person_name: "Administrador", reason: "Revisión documental" });
  expect(screen.getAllByRole("radio")).toHaveLength(2);
});
