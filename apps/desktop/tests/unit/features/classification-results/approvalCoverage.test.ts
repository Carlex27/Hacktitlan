import { describe, expect, it } from "vitest";
import { approvalCoverage } from "@/features/classification-results/model/approvalCoverage";
import { createFakeCertificate, createFakeClassificationRun } from "../../../support/fakeBackend";

describe("approvalCoverage", () => {
  it("exige datos del acta correspondiente", () => {
    expect(approvalCoverage(null, createFakeClassificationRun())).toBeNull();
    expect(approvalCoverage(createFakeCertificate({ id: 99 }), createFakeClassificationRun())).toBeNull();
  });
  it("detecta rollos omitidos y coladas sin productos", () => {
    const certificate = createFakeCertificate();
    expect(approvalCoverage(certificate, createFakeClassificationRun({ results: [] }))?.complete).toBe(false);
    const uncovered = { ...certificate, heats: [...certificate.heats, { id: 2, heat_no: "C-2", standard: null, grade: null }] };
    expect(approvalCoverage(uncovered, createFakeClassificationRun())?.pendingHeats.map((heat) => heat.id)).toEqual([2]);
    expect(approvalCoverage(createFakeCertificate({ heats: [], products: [] }), createFakeClassificationRun({ results: [] }))?.complete).toBe(false);
  });
  it.each(["missing", "conflict", "unknown", "not_matched", "optional"])("comprueba las condiciones del candidato seleccionado: %s", (scenario) => {
    const run = createFakeClassificationRun();
    const result = run.results[0];
    const candidate = result?.candidates[0];
    if (!result || !candidate) throw new Error("Fixture incompleta");
    const pending = { ...run, results: [{ ...result, candidates: [{ ...candidate,
      details: scenario === "missing" ? { missing_fields: ["composition_pct.Cr"] } : scenario === "conflict" ? { conflicts: ["coated"] } : {},
      factors: ["unknown", "not_matched", "optional"].includes(scenario) ? [{ id: 1, sequence: 1, rule_code: "nico", outcome: scenario === "not_matched" ? "not_matched" as const : "unknown" as const,
        required_for_selection: scenario !== "optional", operator: null, expected: {}, observed: {}, unit: null, explanation: "Verificar NICO", evidence_links: [] }] : [],
    }] }] };
    const coverage = approvalCoverage(createFakeCertificate(), pending);
    expect(coverage?.complete).toBe(["missing", "unknown", "optional"].includes(scenario));
    expect(coverage?.pendingConditions).toHaveLength(["missing", "unknown", "optional"].includes(scenario) ? 0 : 1);
  });
  it.each(["current_selection", "fraction", "nico", "outcome"] as const)("no confunde %s ausente o pendiente con autorización", (field) => {
    const run = createFakeClassificationRun();
    const result = run.results[0];
    if (!result) throw new Error("La prueba requiere un resultado");
    const pending = { ...run, results: [{ ...result, [field]: field === "outcome" ? "needs_review" : null }] };
    expect(approvalCoverage(createFakeCertificate(), pending)?.complete).toBe(false);
  });
});
