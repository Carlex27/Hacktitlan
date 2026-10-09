import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { App } from "@/app";
import type { ClassificationRunDto, EvidenceLinkDto } from "@/lib/api";

import {
  createFakeBackend,
  createFakeCertificate,
  createFakeClassificationRun,
  envelope,
  healthyRoutes,
  pdfFile,
  pdfResponse,
  type RouteHandler,
} from "../support/fakeBackend";

const SOURCE_FILE = "/api/v1/rule-sources/756ed9e9/file";
const SOURCE_NAME = "LIGIE capítulo 72 (fuente proporcionada)";

function ruleSourceLink(id: number, page: number | null): EvidenceLinkDto {
  return {
    id,
    source_type: "rule_source",
    field_path: null,
    observation_id: null,
    reference: {
      rule_code: "chapter72.nico.7208.52",
      source_hash: "756ed9e9",
      legal_status: "SIN VIGENCIA — NO VERIFICADO",
      file_url: SOURCE_FILE,
      page_number: page,
      bbox: null,
      source_text: "De espesor superior o igual a 4.75 mm pero inferior o igual a 10 mm",
      can_focus_region: false,
      fallback: "full_page",
      catalog_code: "7208.52.01-01",
    },
    detail_url: `/api/v1/evidence/${id}`,
  };
}

/** Run de prueba: sólo el candidato 7208.52 trae referencia a la fuente. */
function runWithSource(page: number | null): ClassificationRunDto {
  const run = createFakeClassificationRun();
  const result = run.results[0];
  if (!result) throw new Error("Run de prueba sin resultado");
  return {
    ...run,
    results: [
      {
        ...result,
        candidates: result.candidates.map((candidate) =>
          candidate.id === 302
            ? {
                ...candidate,
                factors: [
                  {
                    id: 900,
                    sequence: 1,
                    rule_code: "chapter72.nico.7208.52",
                    outcome: "matched",
                    operator: null,
                    expected: {},
                    observed: {},
                    unit: null,
                    explanation: "Coincide con el NICO",
                    required_for_selection: true,
                    evidence_links: [ruleSourceLink(950, page)],
                  },
                ],
              }
            : candidate,
        ),
      },
    ],
  };
}

function ligieFrame(): HTMLIFrameElement | undefined {
  return screen
    .queryAllByTitle(SOURCE_NAME)
    .find((element): element is HTMLIFrameElement => element instanceof HTMLIFrameElement);
}

async function openValidationTab(run: ClassificationRunDto, extraRoutes: Record<string, RouteHandler> = {}) {
  const backend = createFakeBackend({
    ...healthyRoutes,
    "POST /api/v1/documents": () =>
      envelope({ document_id: 10, certificate_id: 42, job_id: null, duplicate: false }, 200),
    "GET /api/v1/certificates/42": () => envelope(createFakeCertificate({ id: 42 })),
    "GET /api/v1/certificates/42/classification-runs": () =>
      envelope([
        { id: 101, rule_set_id: 1, parent_run_id: null, approval_status: "needs_review", demo_notice: "", created_at: "2024-05-16T10:00:00Z" },
      ]),
    "GET /api/v1/classification-runs/101": () => envelope(run),
    [`GET ${SOURCE_FILE}`]: () => pdfResponse("ligie.pdf"),
    ...extraRoutes,
  });
  const user = userEvent.setup();
  render(<App apiClient={backend.client} />);
  await user.upload(await screen.findByLabelText(/seleccionar certificados pdf/i), pdfFile("acta.pdf"));
  await user.click(await screen.findByRole("button", { name: /revisar/i }));
  const sections = screen.getByRole("navigation", { name: "Secciones de validación" });
  await user.click(within(sections).getByRole("button", { name: "Validación" }));
  await screen.findByRole("radiogroup", { name: "Candidatos disponibles" });
  return { user, backend };
}

describe("Referencia del NICO en la LIGIE", () => {
  it("abre el PDF fuente en la página que indica el backend, al lado de la clasificación", async () => {
    const { user, backend } = await openValidationTab(runWithSource(24));

    const candidates = screen.getByRole("radiogroup", { name: "Candidatos disponibles" });
    const radios = within(candidates).getAllByRole("radio");
    expect(radios[0]).toBeChecked();
    // Sólo hay botón donde el backend adjuntó una referencia.
    expect(within(candidates).queryByRole("button", { name: /ver 7208\.51\.01 en la ligie/i })).toBeNull();

    await user.click(within(candidates).getByRole("button", { name: /ver 7208\.52\.01 en la ligie/i }));

    const ligieTab = await screen.findByRole("tab", { name: "LIGIE p. 24" });
    expect(ligieTab).toHaveAttribute("aria-selected", "true");
    await waitFor(() => expect(ligieFrame()?.getAttribute("src")).toMatch(/^blob:.*#page=24$/));
    expect(backend.calls).toContain(`GET ${SOURCE_FILE}`);
    expect(screen.getByText("7208.52.01-01")).toBeInTheDocument();
    expect(screen.getByText("SIN VIGENCIA — NO VERIFICADO")).toBeInTheDocument();

    // Consultar la referencia no cambia el candidato elegido y la clasificación sigue a la vista.
    expect(radios[0]).toBeChecked();
    expect(candidates).toBeVisible();

    await user.click(screen.getByRole("tab", { name: "Acta" }));
    expect(screen.getByRole("tab", { name: "Acta" })).toHaveAttribute("aria-selected", "true");
  });

  it("si el backend no indica la página, lo avisa y abre el inicio del PDF", async () => {
    const { user } = await openValidationTab(runWithSource(null));

    await user.click(screen.getByRole("button", { name: /ver 7208\.52\.01 en la ligie/i }));
    expect(await screen.findByText(/no indicó la página/i)).toBeInTheDocument();
    await waitFor(() => expect(ligieFrame()?.getAttribute("src")).toMatch(/#page=1$/));
  });

  it("una evidencia de regla abre la fuente en su página", async () => {
    const run = runWithSource(24);
    const result = run.results[0];
    const step = result?.steps[0];
    if (!result || !step) throw new Error("Run de prueba incompleto");
    const withRuleStep: ClassificationRunDto = {
      ...run,
      results: [{ ...result, steps: [{ ...step, evidence_links: [ruleSourceLink(951, 31)] }] }],
    };
    const { user } = await openValidationTab(withRuleStep, {
      "GET /api/v1/evidence/951": () =>
        envelope({
          id: 951,
          decision_step_id: 501,
          candidate_factor_id: null,
          source_type: "rule_source",
          reference: ruleSourceLink(951, 31).reference,
        }),
    });

    const [evidenceButton] = screen.getAllByRole("button", { name: /ver evidencia/i });
    await user.click(evidenceButton as HTMLElement);
    await user.click(await screen.findByRole("button", { name: "Ver en la fuente (p. 31)" }));

    expect(await screen.findByRole("tab", { name: "LIGIE p. 31" })).toHaveAttribute("aria-selected", "true");
    await waitFor(() => expect(ligieFrame()?.getAttribute("src")).toMatch(/#page=31$/));
  });
});
