import { describe, expect, it } from "vitest";

import {
  createExport,
  getCertificateQualityReport,
  getClassificationCandidate,
  getExport,
  getOcrModels,
  listDocumentReviews,
  reprocessCertificate,
  runOcrSmokeCheck,
  type ClassificationCandidateDetailDto,
  type DocumentQualityReportDto,
  type DocumentReviewQueueItemDto,
  type ExportStatusDto,
  type OcrModelPackageStatusDto,
  type OcrSmokeCheckDto,
} from "@/lib/api";

import { createFakeBackend, envelope, errorEnvelope } from "../../../support/fakeBackend";

/** Captura el cuerpo JSON enviado para comprobar el contrato. */
function capture() {
  const seen: { body?: unknown } = {};
  return {
    seen,
    handler: (data: unknown) => (init: RequestInit | undefined) => {
      seen.body = init?.body ? JSON.parse(String(init.body)) : undefined;
      return envelope(data);
    },
  };
}

const qualityReport: DocumentQualityReportDto = {
  certificate_id: 42,
  status: "needs_review",
  quality_score: 0.72,
  product_family: "flat_rolled_coil",
  blocking_count: 1,
  warning_count: 1,
  provenance_summary: { digital: 10, ocr: 0 },
  issues: [
    {
      code: "missing_thickness",
      category: "missing",
      severity: "blocking",
      scope: "product",
      field_path: "products[0].thickness_mm",
      message: "Falta el espesor",
      entity_identifier: "R-1",
      raw_value: null,
      normalized_value: null,
      confidence: null,
      page_number: 1,
      bbox: null,
    },
  ],
};

describe("endpoints del backend (commit Merge PR #1)", () => {
  it("obtiene el detalle de un candidato con factores", async () => {
    const candidate: ClassificationCandidateDetailDto = {
      id: 51,
      classification_result_id: 8,
      rank: 1,
      fraction: "72083701",
      nico: "00",
      description: null,
      support_level: "conditional",
      details: {},
      factors: [
        {
          id: 1,
          sequence: 1,
          rule_code: "thickness.range",
          outcome: "missing",
          operator: "between",
          expected: { min: "4.75", max: "10" },
          observed: {},
          unit: "mm",
          explanation: "No se encontró el espesor",
          required_for_selection: true,
          evidence_links: [],
        },
      ],
    };
    const { client, calls } = createFakeBackend({
      "GET /api/v1/classification-candidates/51": () => envelope(candidate),
    });
    const result = await getClassificationCandidate(client, 51);
    expect(calls).toEqual(["GET /api/v1/classification-candidates/51"]);
    expect(result.factors[0]).toMatchObject({ outcome: "missing", required_for_selection: true });
  });

  it("consulta el reporte de calidad del acta", async () => {
    const { client, calls } = createFakeBackend({
      "GET /api/v1/certificates/42/quality-report": () => envelope(qualityReport),
    });
    await expect(getCertificateQualityReport(client, 42)).resolves.toEqual(qualityReport);
    expect(calls).toEqual(["GET /api/v1/certificates/42/quality-report"]);
  });

  it("lista la cola de revisión con y sin filtros", async () => {
    const item: DocumentReviewQueueItemDto = {
      source_file_name: "molino.xlsx",
      revision_number: 1,
      active_job_id: null,
      can_reprocess: true,
      certificate_id: 42,
      document_id: 10,
      certificate_no: null,
      manufacturer: null,
      uploaded_at: "2026-10-08T00:00:00+00:00",
      document_status: "needs_review",
      approval_status: "needs_review",
      quality_score: 0.72,
      blocking_issues_count: 1,
      warning_issues_count: 0,
      issues_summary: [],
    };
    const { client, calls } = createFakeBackend({
      "GET /api/v1/document-reviews": () => envelope([item]),
      "GET /api/v1/document-reviews?limit=20&status_filter=needs_review": () => envelope([]),
    });
    await expect(listDocumentReviews(client)).resolves.toEqual([item]);
    await expect(
      listDocumentReviews(client, { limit: 20, statusFilter: "needs_review" }),
    ).resolves.toEqual([]);
    expect(calls).toEqual([
      "GET /api/v1/document-reviews",
      "GET /api/v1/document-reviews?limit=20&status_filter=needs_review",
    ]);
  });

  it("reprocesa un acta con etapa, persona y motivo", async () => {
    const { seen, handler } = capture();
    const { client } = createFakeBackend({
      "POST /api/v1/certificates/42/reprocess": handler({
        certificate_id: 43,
        job_id: 9,
        stage: "extraction",
        status: "queued",
        quality_report: null,
      }),
    });
    const result = await reprocessCertificate(client, 42, {
      from_stage: "extraction",
      person_name: "Ana López",
      reason: "PDF reemplazado",
    });
    expect(seen.body).toEqual({ from_stage: "extraction", person_name: "Ana López", reason: "PDF reemplazado" });
    // Desde extracción el backend crea una revisión nueva del acta.
    expect(result.certificate_id).toBe(43);
  });

  it("crea una exportación y consulta su estado", async () => {
    const { seen, handler } = capture();
    const status: ExportStatusDto = {
      id: 7,
      format: "xlsx",
      status: "succeeded",
      scope: { certificate_ids: [42] },
      filters: {},
      person_name: "Ana López",
      workstation_name: "EQUIPO-2",
      sha256: "abc",
      stored_file_id: 3,
      error_message: null,
      created_at: "2026-10-08T00:00:00+00:00",
      download_url: "/api/v1/exports/7/file",
    };
    const { client } = createFakeBackend({
      "POST /api/v1/exports": handler({ export_id: 7, job_id: 12 }),
      "GET /api/v1/exports/7": () => envelope(status),
    });

    const created = await createExport(client, { certificate_ids: [42], person_name: "Ana López" });
    expect(seen.body).toEqual({ certificate_ids: [42], person_name: "Ana López" });
    const current = await getExport(client, created.export_id);
    expect(current.download_url && client.url(current.download_url)).toBe(
      "http://backend.test/api/v1/exports/7/file",
    );
  });

  it("propaga el rechazo de un reporte oficial con actas sin aprobar", async () => {
    const { client } = createFakeBackend({
      "POST /api/v1/exports": () =>
        errorEnvelope("official_export_requires_approval", "Un reporte oficial sólo admite actas aprobadas", 409),
    });
    await expect(
      createExport(client, { certificate_ids: [42], official: true, person_name: "Ana López" }),
    ).rejects.toMatchObject({ kind: "server", code: "official_export_requires_approval", status: 409 });
  });

  it("consulta los modelos de OCR y ejecuta la verificación", async () => {
    const models: OcrModelPackageStatusDto = {
      name: "PP-StructureV3",
      version: "3.0",
      status: "not_installed",
      installed_files: 0,
      total_files: 4,
      installed_bytes: 0,
      total_bytes: 52428800,
      backend: "paddle",
      message: "Modelos no instalados",
    };
    const smoke: OcrSmokeCheckDto = {
      success: false,
      requested_device: "auto",
      effective_device: null,
      elapsed_ms: 0,
      paddle_version: null,
      paddleocr_version: null,
      message: "Paquete OCR no instalado",
    };
    const { client, calls } = createFakeBackend({
      "GET /api/v1/ocr/models": () => envelope(models),
      "POST /api/v1/ocr/smoke-check": () => envelope(smoke),
    });
    await expect(getOcrModels(client)).resolves.toEqual(models);
    await expect(runOcrSmokeCheck(client)).resolves.toEqual(smoke);
    expect(calls).toEqual(["GET /api/v1/ocr/models", "POST /api/v1/ocr/smoke-check"]);
  });
});
