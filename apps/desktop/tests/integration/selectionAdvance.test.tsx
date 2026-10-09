import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { AppProviders } from "@/app/providers/AppProviders";
import { ClassificationValidationTab } from "@/features/classification-results";
import { es } from "@/lib/i18n";
import { createFakeBackend, createFakeClassificationRun, envelope, errorEnvelope } from "../support/fakeBackend";

function setup(fail = false) {
  const run = createFakeClassificationRun();
  const first = run.results[0];
  if (!first) throw new Error("La prueba necesita un resultado");
  run.results = Array.from({ length: 11 }, (_, index) => ({ ...first, id: 201 + index, product_id: index + 1 }));
  const backend = createFakeBackend({
    "POST /api/v1/classification-results/": () => fail ? errorEnvelope("CONFLICT", "No se pudo guardar", 409) : envelope({ candidate_id: 301 }),
  });
  const reload = vi.fn();
  render(<AppProviders apiClient={backend.client}><ClassificationValidationTab run={run} onViewEvidence={vi.fn()} onReloadRun={reload} /></AppProviders>);
  return { user: userEvent.setup(), reload, backend };
}

function activeResult() {
  return screen.getAllByRole("button").find((button) => button.getAttribute("aria-pressed") === "true");
}

describe("Avance tras elegir fracción", () => {
  it("avanza tras guardar, abre la página siguiente y permanece en el último resultado", async () => {
    const { user, reload, backend } = setup();
    const first = activeResult()?.textContent;
    await user.click(screen.getByRole("button", { name: es.classification.selectCandidateBtn }));
    expect(activeResult()?.textContent).not.toBe(first);
    expect(reload).toHaveBeenCalledTimes(1);
    for (let index = 0; index < 9; index++) {
      await user.click(screen.getByRole("button", { name: es.classification.selectCandidateBtn }));
    }
    expect(screen.getByRole("button", { name: es.classification.nextPage })).toBeDisabled();
    const last = activeResult()?.textContent;
    await user.click(screen.getByRole("button", { name: es.classification.selectCandidateBtn }));
    expect(activeResult()?.textContent).toBe(last);
    expect(backend.calls.at(-1)).toBe("POST /api/v1/classification-results/211/select");
  });
  it("no avanza ni recarga ante error", async () => {
    const { user, reload } = setup(true);
    const first = activeResult()?.textContent;
    await user.click(screen.getByRole("button", { name: es.classification.selectCandidateBtn }));
    expect(await screen.findByText("No se pudo guardar")).toBeVisible();
    expect(activeResult()?.textContent).toBe(first);
    expect(reload).not.toHaveBeenCalled();
  });
  it("quitar la selección recarga sin avanzar", async () => {
    const { user, reload } = setup();
    const first = activeResult()?.textContent;
    await user.click(screen.getByRole("button", { name: es.classification.deselectCandidateBtn }));
    expect(activeResult()?.textContent).toBe(first);
    expect(reload).toHaveBeenCalledTimes(1);
  });
});
