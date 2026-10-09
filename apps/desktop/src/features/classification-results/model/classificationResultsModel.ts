import type { ReactNode } from "react";

import type {
  ClassificationOutcomeDto,
  ClassificationResultDto,
  DecisionStepOutcomeDto,
} from "@/lib/api";
import type { ProcessingStatus } from "@/types";

/** Formatea fracción y NICO legal sin inventar ceros ni cadenas vacías. */
export function formatTariffCode(fraction: string | null, nico: string | null): string {
  if (!fraction || fraction.trim().length === 0) {
    return "Sin determinar";
  }
  const cleanFraction = fraction.trim();
  const cleanNico = nico?.trim();
  if (cleanNico && cleanNico.length > 0) {
    return `${cleanFraction}.${cleanNico}`;
  }
  return cleanFraction;
}

/** Mapea el outcome del backend al estado visual estándar. */
export function outcomeToProcessingStatus(
  outcome: ClassificationOutcomeDto | DecisionStepOutcomeDto | string,
): ProcessingStatus {
  switch (outcome) {
    case "classified":
    case "matched":
      return "success";
    case "needs_review":
    case "missing":
    case "ambiguous":
      return "needs_review";
    case "out_of_scope":
    case "not_matched":
      return "error";
    default:
      return "empty";
  }
}

export interface ReviewIndicator {
  ruleCode: string;
  explanation: string;
  outcome: string;
}

/** Extrae pasos con resultado ambiguo o faltante sin inventar categorías ficticias. */
export function extractReviewIndicators(
  result: ClassificationResultDto | null,
): readonly ReviewIndicator[] {
  if (!result || !result.steps) return [];

  const indicators: ReviewIndicator[] = [];

  for (const step of result.steps) {
    if (step.outcome === "missing" || step.outcome === "ambiguous") {
      indicators.push({
        ruleCode: step.rule_code,
        explanation: step.explanation ?? `Regla ${step.rule_code} con resultado ${step.outcome}`,
        outcome: step.outcome,
      });
    }
  }

  return indicators;
}

/**
 * Resultado a mostrar: el elegido si sigue existiendo en la ejecución, o el
 * primero. Una ejecución tiene un resultado por producto (cantidad dinámica).
 */
export function findActiveResult(
  results: readonly ClassificationResultDto[],
  selectedResultId: number | null,
): ClassificationResultDto | null {
  if (selectedResultId !== null) {
    const match = results.find((result) => result.id === selectedResultId);
    if (match) return match;
  }
  return results[0] ?? null;
}

/** Slot para una acción junto a un código arancelario mostrado. */
export type TariffActionRenderer = (
  fraction: string | null,
  nico: string | null,
  displayCode: string,
) => ReactNode;
