import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { App } from "@/app";
import type { ClassificationResultDto, ClassificationRunDto } from "@/lib/api";

import {
  createFakeBackend,
  createFakeCertificate,
  createFakeClassificationRun,
  createFakeEvidence,
  envelope,
  errorEnvelope,
  healthyRoutes,
  pdfFile,
  type RouteHandler,
} from "../support/fakeBackend";

const RUN_SUMMARY = {
  id: 101,
  rule_set_id: 1,
  parent_run_id: null,
  approval_status: "needs_review",
  demo_notice: "Reglas demo",
  created_at: "2024-05-16T10:00:00Z",
};

/** Responde con error las primeras `failures` llamadas y después con `ok`. */
function failingThen(failures: number, ok: () => Response): RouteHandler {
  let calls = 0;
  return () => {
    calls += 1;
    return calls <= failures
      ? errorEnvelope("internal_error", "Ocurrió un error interno", 500)
      : ok();
  };
}

function backendWith(routes: Record<string, RouteHandler>, run: ClassificationRunDto = createFakeClassificationRun()) {
  return createFakeBackend({
    ...healthyRoutes,
    "POST /api/v1/documents": () =>
      envelope({ document_id: 10, certificate_id: 42, job_id: null, duplicate: false }, 200),
    "GET /api/v1/certificates/42": () => envelope(createFakeCertificate({ id: 42 })),
    "GET /api/v1/certificates/42/classification-runs": () => envelope([RUN_SUMMARY]),
    "GET /api/v1/classification-runs/101": () => envelope(run),
    ...routes,
  });
}

async function openValidation(backend: ReturnType<typeof createFakeBackend>) {
  const user = userEvent.setup();
  render(<App apiClient={backend.client} />);
  await user.upload(await screen.findByLabelText(/seleccionar certificados pdf/i), pdfFile("acta.pdf"));
  await user.click(await screen.findByRole("button", { name: /revisar/i }));
  return user;
}

async function openTab(user: ReturnType<typeof userEvent.setup>, name: string) {
  const tabs = screen.getByRole("navigation", { name: "Secciones de validación" });
  await user.click(within(tabs).getByRole("button", { name }));
}

describe("Validación: todos los productos de la ejecución", () => {
  it("permite revisar cada producto y muestra el historial de todos", async () => {
    const base = createFakeClassificationRun();
    const first = base.results[0] as ClassificationResultDto;
    const secondSelection = { id: 402, candidate_id: 311, supersedes_selection_id: null, person_name: "Luis Gómez", reason: "Revisión de bobina", workstation_name: "Estación 2", created_at: "2024-05-17T09:00:00Z" };
    const second: ClassificationResultDto = {
      ...first,
      id: 202,
      product_id: 2,
      product_type: "Bobina laminada en frío",
      fraction: null,
      nico: null,
      outcome: "needs_review",
      candidates: [
        { id: 311, rank: 1, fraction: "7209.16", nico: "99", description: "Segundo producto", support_level: "conditional", details: {}, detail_url: "/api/v1/classification-candidates/311", factors: [] },
      ],
      current_selection: secondSelection,
      selections: [secondSelection],
    };
    const backend = backendWith({}, { ...base, results: [first, second] });

    const user = await openValidation(backend);
    await openTab(user, "Validación");

    const selector = await screen.findByRole("region", { name: /productos clasificados \(2\)/i });
    const productButtons = within(selector).getAllByRole("button");
    expect(productButtons).toHaveLength(2);
    expect(productButtons[0]).toHaveAttribute("aria-pressed", "true");
    expect(screen.queryByText("Segundo producto")).not.toBeInTheDocument();

    await user.click(within(selector).getByRole("button", { name: /producto 2 · bobina laminada en frío/i }));
    expect(productButtons[1]).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByText("Segundo producto")).toBeInTheDocument();
    // Un dato ausente no se presenta como cero ni vacío.
    expect(within(selector).getByText("Sin determinar")).toBeInTheDocument();

    expect(screen.getByText(/el dictamen aplica a los 2 productos/i)).toBeInTheDocument();

    await openTab(user, "Historial");
    expect(screen.getByText("María Pérez")).toBeInTheDocument();
    expect(screen.getByText("Luis Gómez")).toBeInTheDocument();
  });
});

describe("Validación: las fallas se muestran, no se esconden", () => {
  it("muestra el error del acta y se recupera al reintentar", async () => {
    const backend = backendWith({
      "GET /api/v1/certificates/42": failingThen(1, () =>
        envelope(createFakeCertificate({ id: 42, manufacturer: "Fabricante Recuperado" })),
      ),
    });

    const user = await openValidation(backend);

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("No se pudieron cargar los datos del acta");
    expect(alert).toHaveTextContent("Ocurrió un error interno");
    expect(screen.queryByText("Seleccione un acta para consultar su información.")).not.toBeInTheDocument();

    await user.click(within(alert).getByRole("button", { name: "Reintentar" }));
    expect(await screen.findByText("Fabricante Recuperado")).toBeInTheDocument();
  });

  it("muestra el error de la clasificación en Validación e Historial", async () => {
    const backend = backendWith({
      "GET /api/v1/certificates/42/classification-runs": failingThen(1, () => envelope([RUN_SUMMARY])),
    });

    const user = await openValidation(backend);
    await openTab(user, "Validación");

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("No se pudo cargar la clasificación");
    expect(screen.queryByText("Sin ejecuciones de clasificación")).not.toBeInTheDocument();

    await openTab(user, "Historial");
    expect(screen.getByRole("alert")).toHaveTextContent("No se pudo cargar la clasificación");

    await user.click(within(screen.getByRole("alert")).getByRole("button", { name: "Reintentar" }));
    expect(await screen.findByText("María Pérez")).toBeInTheDocument();
  });
});

describe("Validación: evidencia", () => {
  it("muestra el error de la evidencia y permite reintentar", async () => {
    const backend = backendWith({
      "GET /api/v1/evidence/601": failingThen(1, () => envelope(createFakeEvidence())),
    });

    const user = await openValidation(backend);
    await openTab(user, "Validación");

    const [evidenceButton] = await screen.findAllByRole("button", { name: /ver evidencia/i });
    expect(evidenceButton).toBeDefined();
    await user.click(evidenceButton as HTMLElement);

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("No se pudo cargar la evidencia");

    await user.click(within(alert).getByRole("button", { name: "Reintentar" }));
    expect(await screen.findByText("Espesor: 12.70 mm")).toBeInTheDocument();
  });

  it("si se abren dos evidencias seguidas, gana la última", async () => {
    let releaseFirst: (() => void) | undefined;
    const firstGate = new Promise<void>((resolve) => {
      releaseFirst = resolve;
    });
    const run = createFakeClassificationRun();
    const result = run.results[0] as ClassificationResultDto;
    const step = result.steps[0];
    const link = step?.evidence_links[0];
    if (!step || !link) throw new Error("Falta el paso de prueba");
    const steps = [
      step,
      {
        ...step,
        id: 502,
        sequence: 2,
        rule_code: "RULE_WIDTH",
        evidence_links: [{ ...link, id: 602, detail_url: "/api/v1/evidence/602" }],
      },
    ];
    const backend = backendWith(
      {
        "GET /api/v1/evidence/601": async () => {
          await firstGate;
          return envelope(createFakeEvidence({ id: 601 }));
        },
        "GET /api/v1/evidence/602": () =>
          envelope(createFakeEvidence({ id: 602, field_path: "dimensions.width_mm" })),
      },
      { ...run, results: [{ ...result, steps }] },
    );

    const user = await openValidation(backend);
    await openTab(user, "Validación");

    const checklist = (await screen.findByRole("heading", { name: "Evaluación de reglas", level: 4 })).closest("section");
    expect(checklist).not.toBeNull();
    const buttons = within(checklist as HTMLElement).getAllByRole("button", { name: /ver evidencia/i });
    await user.click(buttons[0] as HTMLElement);
    await user.click(buttons[1] as HTMLElement);

    expect(await screen.findByText("dimensions.width_mm")).toBeInTheDocument();
    releaseFirst?.();
    await waitFor(() => expect(screen.getByText("dimensions.width_mm")).toBeInTheDocument());
    expect(screen.queryByText(/#601/)).not.toBeInTheDocument();
  });
});

describe("Validación: selección vigente", () => {
  it("marca el candidato de `current_selection` del backend, no el último del historial", async () => {
    const run = createFakeClassificationRun();
    const result = run.results[0] as ClassificationResultDto;
    const vigente = { id: 405, candidate_id: 302, supersedes_selection_id: null, person_name: "Ana", reason: "Vigente", workstation_name: "E1", created_at: "2024-05-18T09:00:00Z" };
    const backend = backendWith({}, {
      ...run,
      results: [{ ...result, current_selection: vigente, selections: [vigente, ...result.selections] }],
    });

    const user = await openValidation(backend);
    await openTab(user, "Validación");

    const candidates = await screen.findByRole("radiogroup", { name: "Candidatos disponibles" });
    const radios = within(candidates).getAllByRole("radio");
    expect(radios).toHaveLength(2);
    expect(radios[1]).toBeChecked();
    expect(radios[0]).not.toBeChecked();
  });
});
