import type {
  ClassificationCandidateDto,
  ClassificationResultDto,
  EvidenceLinkDto,
  JsonObject,
} from "@/lib/api";

/**
 * Ubicación en la fuente normativa (PDF LIGIE) que el backend adjunta a la
 * evidencia de tipo `rule_source`. La página y el texto los decide el backend.
 */
export interface SourceReference {
  /** Ruta del PDF en el API, p. ej. `/api/v1/rule-sources/{hash}/file`. */
  filePath: string;
  page: number | null;
  sourceText: string | null;
  legalStatus: string | null;
  /** Código del catálogo citado (p. ej. `7208.51.01-00`), si el backend lo indica. */
  catalogCode: string | null;
  ruleCode: string | null;
}

function stringOrNull(value: unknown): string | null {
  return typeof value === "string" && value.trim().length > 0 ? value : null;
}

function positiveIntOrNull(value: unknown): number | null {
  return typeof value === "number" && Number.isInteger(value) && value > 0 ? value : null;
}

/** Interpreta `reference` de una evidencia; `null` si no apunta a un PDF fuente. */
export function readSourceReference(reference: JsonObject): SourceReference | null {
  const filePath = stringOrNull(reference.file_url);
  if (filePath === null) return null;
  return {
    filePath,
    page: positiveIntOrNull(reference.page_number),
    sourceText: stringOrNull(reference.source_text),
    legalStatus: stringOrNull(reference.legal_status),
    catalogCode: stringOrNull(reference.catalog_code),
    ruleCode: stringOrNull(reference.rule_code),
  };
}

/** Prioridad de reglas para citar un código: primero NICO, luego fracción. */
function rulePriority(ruleCode: string): number {
  if (ruleCode.startsWith("chapter72.nico.")) return 0;
  if (ruleCode.includes("fraction")) return 1;
  return 2;
}

function firstReference(
  sources: readonly { ruleCode: string; links: readonly EvidenceLinkDto[] }[],
): SourceReference | null {
  const ordered = [...sources].sort((a, b) => rulePriority(a.ruleCode) - rulePriority(b.ruleCode));
  let withoutPage: SourceReference | null = null;
  for (const source of ordered) {
    for (const link of source.links) {
      if (link.source_type !== "rule_source") continue;
      const reference = readSourceReference(link.reference);
      if (reference === null) continue;
      if (reference.page !== null) return reference;
      withoutPage ??= reference;
    }
  }
  return withoutPage;
}

/** Referencia del candidato (fracción + NICO) a partir de sus factores. */
export function findCandidateSourceReference(
  candidate: ClassificationCandidateDto,
): SourceReference | null {
  return firstReference(
    candidate.factors.map((factor) => ({ ruleCode: factor.rule_code, links: factor.evidence_links })),
  );
}

function digits(value: string | null): string {
  return value?.replace(/\D/g, "") ?? "";
}

/**
 * Referencia del código que se muestra para un resultado: la del candidato con
 * esa fracción y NICO; si ninguno coincide, la de los pasos de decisión.
 */
export function findSourceReferenceForCode(
  result: ClassificationResultDto,
  fraction: string | null,
  nico: string | null,
): SourceReference | null {
  if (digits(fraction) === "") return null;
  const candidate = result.candidates.find(
    (item) => digits(item.fraction) === digits(fraction) && digits(item.nico) === digits(nico),
  );
  return (
    (candidate ? findCandidateSourceReference(candidate) : null) ??
    firstReference(result.steps.map((step) => ({ ruleCode: step.rule_code, links: step.evidence_links })))
  );
}
