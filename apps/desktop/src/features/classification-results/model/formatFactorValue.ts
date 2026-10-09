import type { JsonValue } from "@/lib/api";
import { es } from "@/lib/i18n";

function label(key: string): string {
  const labels: Readonly<Record<string, string>> = es.workspace.factorFields;
  return labels[key] ?? key.replaceAll("_", " ");
}

/** Presentation only: preserve the server's values and condition structure. */
export function formatFactorValue(value: JsonValue, unit: string | null = null): string[] {
  if (value === null) return [es.workspace.unknown];
  if (Array.isArray(value)) {
    return value.length ? value.flatMap((item) => formatFactorValue(item, unit)) : [es.workspace.unknown];
  }
  if (typeof value === "object") {
    const entries = Object.entries(value);
    return entries.length ? entries.flatMap(([key, item]) =>
      formatFactorValue(item, unit).map((line) => `${label(key)}: ${line}`),
    ) : [es.workspace.unknown];
  }
  if (typeof value === "boolean") return [value ? es.workspace.yes : es.workspace.no];
  const terms: Readonly<Record<string, string>> = es.workspace.factorTerms;
  const text = terms[String(value)] ?? String(value);
  return [unit ? `${text} ${unit}` : text];
}
