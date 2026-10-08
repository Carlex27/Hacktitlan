import { describe, expect, it } from "vitest";

import type {
  ClassificationResultDto,
} from "@/lib/api";
import {
  extractReviewIndicators,
  findActiveResult,
  formatTariffCode,
  outcomeToProcessingStatus,
} from "@/features/classification-results/model";

describe("classificationResultsModel", () => {

  describe("formatTariffCode", () => {
    it("devuelve 'Sin determinar' cuando la fracción es null o vacía", () => {
      expect(formatTariffCode(null, null)).toBe("Sin determinar");
      expect(formatTariffCode("", "")).toBe("Sin determinar");
      expect(formatTariffCode("   ", null)).toBe("Sin determinar");
    });

    it("concatena fracción y NICO cuando ambos están presentes", () => {
      expect(formatTariffCode("7208.51", "01")).toBe("7208.51.01");
    });

    it("devuelve sólo la fracción cuando NICO es null o vacío", () => {
      expect(formatTariffCode("7208.51", null)).toBe("7208.51");
      expect(formatTariffCode("7208.51", "")).toBe("7208.51");
    });
  });

  describe("outcomeToProcessingStatus", () => {
    it("mapea resultados esperados a estados visuales", () => {
      expect(outcomeToProcessingStatus("classified")).toBe("success");
      expect(outcomeToProcessingStatus("matched")).toBe("success");
      expect(outcomeToProcessingStatus("needs_review")).toBe("needs_review");
      expect(outcomeToProcessingStatus("missing")).toBe("needs_review");
      expect(outcomeToProcessingStatus("ambiguous")).toBe("needs_review");
      expect(outcomeToProcessingStatus("out_of_scope")).toBe("error");
      expect(outcomeToProcessingStatus("not_matched")).toBe("error");
      expect(outcomeToProcessingStatus("unknown_status")).toBe("empty");
    });
  });

  describe("extractReviewIndicators", () => {
    it("extrae pasos con resultado ambiguo o faltante sin inventar riesgos ficticios", () => {
      const result: ClassificationResultDto = {
        id: 1,
        product_id: 1,
        product_type: "Placa",
        fraction: "7208.51",
        nico: "01",
        description: "Placa",
        outcome: "needs_review",
        details: {},
        candidates: [],
        current_selection: null,
        selections: [],
        steps: [
          {
            id: 1,
            sequence: 1,
            rule_code: "R1",
            outcome: "matched",
            inputs: {},
            evidence: [],
            evidence_links: [],
            explanation: "OK",
          },
          {
            id: 2,
            sequence: 2,
            rule_code: "R_CARBON",
            outcome: "missing",
            inputs: {},
            evidence: [],
            evidence_links: [],
            explanation: "Falta porcentaje de carbono",
          },
          {
            id: 3,
            sequence: 3,
            rule_code: "R_ROLLING",
            outcome: "ambiguous",
            inputs: {},
            evidence: [],
            evidence_links: [],
            explanation: "No se distingue laminado en frío o caliente",
          },
        ],
      };

      const indicators = extractReviewIndicators(result);
      expect(indicators).toHaveLength(2);
      expect(indicators[0]?.ruleCode).toBe("R_CARBON");
      expect(indicators[0]?.outcome).toBe("missing");
      expect(indicators[1]?.ruleCode).toBe("R_ROLLING");
      expect(indicators[1]?.outcome).toBe("ambiguous");
    });

    it("devuelve arreglo vacío cuando no hay pasos en revisión", () => {
      expect(extractReviewIndicators(null)).toEqual([]);
    });
  });
});

describe("findActiveResult", () => {
  const results = [
    { id: 1 } as ClassificationResultDto,
    { id: 2 } as ClassificationResultDto,
  ];

  it("devuelve el resultado elegido si existe", () => {
    expect(findActiveResult(results, 2)?.id).toBe(2);
  });

  it("vuelve al primero si no hay elección o ya no existe", () => {
    expect(findActiveResult(results, null)?.id).toBe(1);
    expect(findActiveResult(results, 99)?.id).toBe(1);
  });

  it("devuelve null sin resultados", () => {
    expect(findActiveResult([], 1)).toBeNull();
  });
});
