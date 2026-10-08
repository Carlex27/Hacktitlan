import { describe, expect, it } from "vitest";

import {
  getClassificationRun,
  getEvidence,
  getOcrStatus,
  listClassificationRuns,
  selectClassificationCandidate,
  type ClassificationRunDto,
  type EvidenceDetailDto,
  type OcrStatusDto,
} from "@/lib/api";

import { createFakeBackend, envelope, errorEnvelope, TEST_BASE_URL } from "../../../support/fakeBackend";

const ocrStatus: OcrStatusDto = {
  enabled: false,
  installed: false,
  healthy: false,
  compatibility: "supported_with_limits",
  selected_device: null,
  paddle_version: null,
  paddleocr_version: null,
  hardware: {
    architecture: "AMD64",
    operating_system: "Windows",
    total_memory_mb: 8192,
    available_memory_mb: null,
    gpus: [],
    compatibility: "supported_with_limits",
    reasons: ["Sin GPU dedicada"],
  },
  message: "El paquete OCR no está instalado",
};

const run: ClassificationRunDto = {
  id: 4,
  certificate_id: 21,
  rule_set_id: 1,
  parent_run_id: null,
  approval_status: "needs_review",
  input_snapshot: {},
  demo_notice: "DEMOSTRACIÓN — SIN VALIDEZ ADUANERA",
  results: [
    {
      id: 8,
      product_id: 30,
      product_type: "laminado plano",
      fraction: null,
      nico: null,
      description: null,
      outcome: "needs_review",
      details: {},
      candidates: [
        {
          id: 51,
          rank: 1,
          fraction: "72083701",
          nico: "00",
          description: null,
          support_level: "conditional",
          details: {},
        },
      ],
      selections: [],
      steps: [
        {
          id: 70,
          sequence: 1,
          rule_code: "chapter72.family",
          outcome: "matched",
          inputs: {},
          evidence: [],
          evidence_links: [
            {
              id: 90,
              source_type: "observation",
              field_path: "products[0].thickness_mm",
              observation_id: 12,
              reference: {},
              detail_url: "/api/v1/evidence/90",
            },
          ],
          explanation: null,
        },
      ],
    },
  ],
};

const evidence: EvidenceDetailDto = {
  id: 90,
  decision_step_id: 70,
  source_type: "observation",
  field_path: "products[0].thickness_mm",
  observation: {
    id: 12,
    raw_value: "4,75",
    normalized_value: 4.75,
    unit: "mm",
    confidence: null,
    source_text: "THK 4,75",
  },
  document: { id: 5, file_url: "/api/v1/documents/5/file" },
  focus: { page_number: 1, bbox: null, can_focus_region: false, fallback: "full_page" },
};

describe("endpoints del commit Backend", () => {
  it("consulta el estado de OCR", async () => {
    const { client, calls } = createFakeBackend({
      "GET /api/v1/ocr/status": () => envelope(ocrStatus),
    });
    await expect(getOcrStatus(client)).resolves.toEqual(ocrStatus);
    expect(calls).toEqual(["GET /api/v1/ocr/status"]);
  });

  it("lista ejecuciones del acta y obtiene el detalle con candidatos y evidencia", async () => {
    const { client, calls } = createFakeBackend({
      "GET /api/v1/certificates/21/classification-runs": () =>
        envelope([{ id: 4, rule_set_id: 1, parent_run_id: null, approval_status: "needs_review", demo_notice: "", created_at: "2026-10-08T00:00:00+00:00" }]),
      "GET /api/v1/classification-runs/4": () => envelope(run),
    });

    const runs = await listClassificationRuns(client, 21);
    const detail = await getClassificationRun(client, runs[0]?.id ?? 0);

    expect(calls).toEqual([
      "GET /api/v1/certificates/21/classification-runs",
      "GET /api/v1/classification-runs/4",
    ]);
    const result = detail.results[0];
    expect(result?.candidates[0]).toMatchObject({ fraction: "72083701", nico: "00" });
    expect(result?.fraction).toBeNull();
    const link = result?.steps[0]?.evidence_links[0];
    expect(link && client.url(link.detail_url)).toBe(`${TEST_BASE_URL}/api/v1/evidence/90`);
  });

  it("envía la selección de candidato como JSON", async () => {
    let body: unknown;
    let contentType: string | null = null;
    const { client, calls } = createFakeBackend({
      "POST /api/v1/classification-results/8/select": (init) => {
        body = JSON.parse(String(init?.body));
        contentType = new Headers(init?.headers).get("Content-Type");
        return envelope({
          selection_id: 3,
          classification_result_id: 8,
          candidate_id: 51,
          fraction: "72083701",
          nico: "00",
          person_name: "Ana López",
          reason: "Espesor confirmado en el acta",
          workstation_name: "EQUIPO-2",
          created_at: "2026-10-08T00:00:00+00:00",
        });
      },
    });

    const selection = await selectClassificationCandidate(client, 8, {
      candidate_id: 51,
      person_name: "Ana López",
      reason: "Espesor confirmado en el acta",
    });

    expect(calls).toEqual(["POST /api/v1/classification-results/8/select"]);
    expect(contentType).toBe("application/json");
    expect(body).toEqual({
      candidate_id: 51,
      person_name: "Ana López",
      reason: "Espesor confirmado en el acta",
    });
    expect(selection).toMatchObject({ fraction: "72083701", nico: "00" });
  });

  it("propaga el rechazo de una selección inválida", async () => {
    const { client } = createFakeBackend({
      "POST /api/v1/classification-results/8/select": () =>
        errorEnvelope("candidate_not_found", "El candidato no pertenece al resultado", 409),
    });
    await expect(
      selectClassificationCandidate(client, 8, { candidate_id: 99, person_name: "Ana", reason: "Prueba" }),
    ).rejects.toMatchObject({ kind: "server", code: "candidate_not_found", status: 409 });
  });

  it("obtiene evidencia y distingue su origen", async () => {
    const { client } = createFakeBackend({
      "GET /api/v1/evidence/90": () => envelope(evidence),
    });
    const detail = await getEvidence(client, 90);
    if (detail.source_type !== "observation") throw new Error("Se esperaba evidencia de observación");
    expect(detail.focus.fallback).toBe("full_page");
    expect(client.url(detail.document.file_url)).toBe(`${TEST_BASE_URL}/api/v1/documents/5/file`);
  });
});
