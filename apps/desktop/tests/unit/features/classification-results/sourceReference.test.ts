import { describe, expect, it } from "vitest";

import {
  findCandidateSourceReference,
  findSourceReferenceForCode,
  readSourceReference,
} from "@/features/classification-results";
import type { ClassificationCandidateDto, ClassificationResultDto, EvidenceLinkDto } from "@/lib/api";

function link(ruleCode: string, page: unknown, sourceType: "rule_source" | "observation" = "rule_source"): EvidenceLinkDto {
  return {
    id: 1,
    source_type: sourceType,
    field_path: null,
    observation_id: null,
    reference: { file_url: "/api/v1/rule-sources/h/file", page_number: page as number, rule_code: ruleCode },
    detail_url: "/api/v1/evidence/1",
  };
}

function candidate(id: number, fraction: string, nico: string, factors: { rule: string; links: EvidenceLinkDto[] }[]): ClassificationCandidateDto {
  return {
    id,
    rank: id,
    fraction,
    nico,
    description: null,
    support_level: "conditional",
    details: {},
    detail_url: `/api/v1/classification-candidates/${id}`,
    factors: factors.map((factor, index) => ({
      id: index,
      sequence: index + 1,
      rule_code: factor.rule,
      outcome: "matched",
      operator: null,
      expected: {},
      observed: {},
      unit: null,
      explanation: "",
      required_for_selection: true,
      evidence_links: factor.links,
    })),
  };
}

describe("readSourceReference", () => {
  it("lee la referencia del backend y descarta páginas inválidas", () => {
    expect(readSourceReference({ file_url: "/f", page_number: 7, legal_status: "SIN VIGENCIA" })).toMatchObject({
      filePath: "/f",
      page: 7,
      legalStatus: "SIN VIGENCIA",
      sourceText: null,
    });
    expect(readSourceReference({ file_url: "/f", page_number: 0 })?.page).toBeNull();
    expect(readSourceReference({ file_url: "/f", page_number: "7" })?.page).toBeNull();
  });

  it("sin archivo no hay referencia", () => {
    expect(readSourceReference({ rule_code: "x" })).toBeNull();
  });
});

describe("findCandidateSourceReference", () => {
  it("prefiere la regla de NICO y una referencia con página", () => {
    const result = findCandidateSourceReference(
      candidate(1, "72085101", "00", [
        { rule: "chapter72.flat_rolled.definition", links: [link("chapter72.flat_rolled.definition", 8)] },
        { rule: "chapter72.nico.720851", links: [link("chapter72.nico.720851", null), link("chapter72.nico.720851", 24)] },
      ]),
    );
    expect(result?.page).toBe(24);
    expect(result?.ruleCode).toBe("chapter72.nico.720851");
  });

  it("ignora evidencia de observaciones y devuelve null si no hay fuente", () => {
    expect(
      findCandidateSourceReference(candidate(1, "1", "1", [{ rule: "x", links: [link("x", 3, "observation")] }])),
    ).toBeNull();
  });
});

describe("findSourceReferenceForCode", () => {
  it("usa el candidato con el mismo código mostrado, con o sin puntos", () => {
    const result = {
      candidates: [
        candidate(1, "72085101", "00", [{ rule: "chapter72.nico.a", links: [link("chapter72.nico.a", 10)] }]),
        candidate(2, "72085201", "01", [{ rule: "chapter72.nico.b", links: [link("chapter72.nico.b", 24)] }]),
      ],
      steps: [],
    } as unknown as ClassificationResultDto;
    expect(findSourceReferenceForCode(result, "7208.52.01", "01")?.page).toBe(24);
    expect(findSourceReferenceForCode(result, null, null)).toBeNull();
  });
});
