import type {
  CertificateChemicalCompositionDto,
  CertificateObservationDto,
} from "@/lib/api";

/** Formatea un valor conservando texto original y adjuntando su unidad. */
export function formatValueWithUnit(value: unknown, unit: string | null = null): string {
  if (value === null || value === undefined || value === "") {
    return "—";
  }
  const str = String(value);
  if (unit && unit.trim().length > 0) {
    return `${str} ${unit.trim()}`;
  }
  return str;
}

export interface FormattedMechanicalProperty {
  id: number;
  fieldPath: string;
  label: string;
  value: string;
  unit: string | null;
  confidence: number | null;
  sourceText: string | null;
  pageNumber: number | null;
}

const MECHANICAL_KEYWORDS = [
  "yield",
  "tensile",
  "elongation",
  "hardness",
  "impact",
  "mecanic",
  "resistencia",
  "elastico",
  "dureza",
  "alargamiento",
];

function deriveMechanicalLabel(fieldPath: string): string {
  const lower = fieldPath.toLowerCase();
  if (lower.includes("yield") || lower.includes("elastico")) return "Límite elástico (Yield)";
  if (lower.includes("tensile") || lower.includes("resistencia")) return "Resistencia a la tracción (Tensile)";
  if (lower.includes("elongation") || lower.includes("alargamiento")) return "Elongación (%)";
  if (lower.includes("hardness") || lower.includes("dureza")) return "Dureza";
  if (lower.includes("impact")) return "Impacto";
  return fieldPath.split(".").pop() ?? fieldPath;
}

/** Filtra observaciones que correspondan a ensayos o propiedades mecánicas. */
export function extractMechanicalProperties(
  observations: readonly CertificateObservationDto[],
): readonly FormattedMechanicalProperty[] {
  return observations
    .filter((obs) => {
      const lower = obs.field_path.toLowerCase();
      return MECHANICAL_KEYWORDS.some((kw) => lower.includes(kw));
    })
    .map((obs) => {
      const displayVal = obs.normalized_value ?? obs.raw_value;
      return {
        id: obs.id,
        fieldPath: obs.field_path,
        label: deriveMechanicalLabel(obs.field_path),
        value: formatValueWithUnit(displayVal, obs.unit),
        unit: obs.unit,
        confidence: obs.confidence,
        sourceText: obs.source_text,
        pageNumber: obs.page_number,
      };
    });
}

export interface FormattedChemicalItem {
  id: number;
  element: string;
  percentageDisplay: string;
  rawPercentage: string | null;
  sourceLabel: string | null;
}

/** Prepara la lista de composición química conservando cadenas exactas. */
export function formatChemicalCompositions(
  chemistry: readonly CertificateChemicalCompositionDto[],
): readonly FormattedChemicalItem[] {
  return chemistry.map((item) => ({
    id: item.id,
    element: item.element,
    percentageDisplay: item.percentage !== null && item.percentage.trim().length > 0 ? `${item.percentage}%` : "—",
    rawPercentage: item.percentage,
    sourceLabel: item.source_label,
  }));
}
