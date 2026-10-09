import { describe, expect, it } from "vitest";

import {
  approveClassificationRun,
  getCertificate,
  getClassificationRun,
  getEvidence,
  getOcrStatus,
  listClassificationRuns,
  rejectClassificationRun,
  selectClassificationCandidate,
  type CertificateDetailDto,
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
  models: {
    name: "PP-StructureV3",
    version: "3.0",
    status: "not_installed",
    installed_files: 0,
    total_files: 4,
    installed_bytes: 0,
    total_bytes: 52428800,
    backend: "paddle",
    message: "Modelos no instalados",
  },
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
          detail_url: "/api/v1/classification-candidates/51",
          factors: [],
        },
      ],
      current_selection: null,
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
  candidate_factor_id: null,
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

  it("obtiene el detalle del acta con composición y productos", async () => {
    const certificateData: CertificateDetailDto = {
      id: 21,
      document_id: 5,
      source_file_name: "molino.xlsx",
      manufacturer: "MOLINO DE PRUEBA",
      certificate_no: "CERT-999",
      certificate_date: "2026-10-08",
      uploaded_at: "2026-10-08T00:00:00Z",
      revision_number: 1,
      previous_revision_id: null,
      approval_status: "needs_review",
      standard: "ASTM A36",
      product_name: "Rollo de acero",
      demo_notice: "DEMO",
      heats: [{ id: 1, heat_no: "H-100", standard: "ASTM A36", grade: "A36" }],
      products: [
        {
          id: 30,
          heat_id: 1,
          product_identifier: "COIL-01",
          label_no: "L1",
          product_type: "laminado",
          form: "flat",
          coiled: true,
          rolling: "hot",
          width_mm: "1500.00",
          thickness_mm: "4.75",
          weight_kg: "24500.00",
        },
      ],
      observations: [
        {
          id: 12,
          heat_id: 1,
          product_id: 30,
          field_path: "products[0].thickness_mm",
          raw_value: "4.75",
          normalized_value: 4.75,
          unit: "mm",
          confidence: null,
          page_number: 1,
          bbox: null,
          source_text: "4.75 mm",
          inherited: false,
          supersedes_id: null,
          is_current: true,
        },
      ],
      chemical_compositions: [
        {
          id: 1,
          heat_id: 1,
          product_id: null,
          element: "C",
          raw_value: "0.15",
          percentage: "0.1500",
          inherited: false,
          source_label: "Carbon",
        },
      ],
    };

    const { client, calls } = createFakeBackend({
      "GET /api/v1/certificates/21": () => envelope(certificateData),
    });

    const cert = await getCertificate(client, 21);
    expect(calls).toEqual(["GET /api/v1/certificates/21"]);
    expect(cert.certificate_no).toBe("CERT-999");
    expect(cert.products[0]?.thickness_mm).toBe("4.75");
    expect(cert.chemical_compositions[0]?.percentage).toBe("0.1500");
  });

  it("aprueba una ejecución de clasificación con persona y motivo", async () => {
    let body: unknown;
    const { client, calls } = createFakeBackend({
      "POST /api/v1/classification-runs/4/approve": (init) => {
        body = JSON.parse(String(init?.body));
        return envelope({ classification_run_id: 4, approval_status: "approved" });
      },
    });

    const result = await approveClassificationRun(client, 4, {
      person_name: "Carlos Ruiz",
      reason: "Fracción arancelaria validada",
    });

    expect(calls).toEqual(["POST /api/v1/classification-runs/4/approve"]);
    expect(body).toEqual({ person_name: "Carlos Ruiz", reason: "Fracción arancelaria validada" });
    expect(result).toEqual({ classification_run_id: 4, approval_status: "approved" });
  });

  it("rechaza una ejecución de clasificación con persona y motivo", async () => {
    let body: unknown;
    const { client, calls } = createFakeBackend({
      "POST /api/v1/classification-runs/4/reject": (init) => {
        body = JSON.parse(String(init?.body));
        return envelope({ classification_run_id: 4, approval_status: "rejected" });
      },
    });

    const result = await rejectClassificationRun(client, 4, {
      person_name: "Carlos Ruiz",
      reason: "Falta información química",
    });

    expect(calls).toEqual(["POST /api/v1/classification-runs/4/reject"]);
    expect(body).toEqual({ person_name: "Carlos Ruiz", reason: "Falta información química" });
    expect(result).toEqual({ classification_run_id: 4, approval_status: "rejected" });
  });
});
