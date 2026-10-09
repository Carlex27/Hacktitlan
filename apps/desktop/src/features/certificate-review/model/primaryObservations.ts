import type { CertificateObservationDto, JsonValue } from "@/lib/api";
import { es } from "@/lib/i18n";

export function primaryObservations(observations: readonly CertificateObservationDto[]) {
  const labels: Readonly<Record<string, string>> = es.workspace.observationFields;
  return observations.filter((observation) => observation.is_current).flatMap((observation) => {
    const label = labels[observation.field_path];
    return label ? [{ ...observation, label }] : [];
  });
}

export function verifiedChemicalObservations(observations: readonly CertificateObservationDto[]) {
  return observations.filter((observation) => observation.is_current
    && observation.field_path.startsWith("composition_pct.")
    && (observation.verification || observation.supersedes_id !== null)).map((observation) => ({
      ...observation, label: es.workspace.chemicalField(observation.field_path.slice("composition_pct.".length)),
    }));
}

export function displayObservationValue(value: JsonValue): string {
  if (value === null) return es.workspace.unknown;
  if (typeof value === "boolean") return value ? es.workspace.yes : es.workspace.no;
  if (Array.isArray(value)) return value.length ? value.map(displayObservationValue).join("; ") : es.workspace.unknown;
  if (typeof value === "object") return Object.values(value).map(displayObservationValue).join("; ") || es.workspace.unknown;
  const terms: Readonly<Record<string, string>> = es.workspace.observationTerms;
  return terms[String(value)] ?? String(value);
}
