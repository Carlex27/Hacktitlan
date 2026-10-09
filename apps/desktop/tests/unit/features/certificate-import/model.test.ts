import { describe, expect, it } from "vitest";

import type { JobDto } from "@/lib/api";

import { describeItem } from "@/features/certificate-import/model/describeItem";
import {
  applyJob,
  applyUpload,
  createImportItem,
  isTerminalPhase,
  phaseToStatus,
  type ImportPhase,
} from "@/features/certificate-import/model/importItem";
import { importReducer } from "@/features/certificate-import/model/importReducer";
import { partitionPdfFiles } from "@/features/certificate-import/model/partitionPdfFiles";

function job(overrides: Partial<JobDto> = {}): JobDto {
  return {
    id: 7,
    document_id: 3,
    kind: "extract_document",
    status: "running",
    progress: 40,
    attempts: 1,
    max_attempts: 3,
    error_code: null,
    error_message: null,
    result: null,
    ...overrides,
  };
}

describe("phaseToStatus", () => {
  it.each<[ImportPhase, string]>([
    ["uploading", "loading"],
    ["queued", "loading"],
    ["running", "loading"],
    ["succeeded", "success"],
    ["needs_review", "needs_review"],
    ["needs_ocr", "needs_review"],
    ["no_job", "needs_review"],
    ["failed", "error"],
    ["cancelled", "error"],
    ["request_failed", "error"],
  ])("%s → %s", (phase, status) => {
    expect(phaseToStatus(phase)).toBe(status);
  });

  it("sólo las fases en curso no son terminales", () => {
    expect(isTerminalPhase("uploading")).toBe(false);
    expect(isTerminalPhase("queued")).toBe(false);
    expect(isTerminalPhase("running")).toBe(false);
    expect(isTerminalPhase("needs_ocr")).toBe(true);
  });
});

describe("applyUpload / applyJob", () => {
  const base = createImportItem("a", "molino.pdf");

  it("queda en cola cuando hay trabajo y conserva el acta", () => {
    const item = applyUpload(base, { document_id: 3, certificate_id: 9, job_id: 7, duplicate: false });
    expect(item).toMatchObject({ phase: "queued", certificateId: 9, jobId: 7, duplicate: false });
  });

  it("marca revisión cuando el servidor no registró trabajo", () => {
    const item = applyUpload(base, { document_id: 3, certificate_id: 9, job_id: null, duplicate: true });
    expect(item.phase).toBe("no_job");
    expect(phaseToStatus(item.phase)).toBe("needs_review");
  });

  it("no convierte un progreso desconocido en cero", () => {
    expect(applyJob(base, job({ progress: null })).progress).toBeNull();
  });

  it("conserva el mensaje de error del trabajo", () => {
    const item = applyJob(base, job({ status: "failed", error_message: "PDF dañado" }));
    expect(item).toMatchObject({ phase: "failed", errorMessage: "PDF dañado" });
  });
});

describe("importReducer", () => {
  it("agrega al inicio, actualiza por id y limpia terminados", () => {
    let items = importReducer([], { type: "added", items: [createImportItem("a", "a.pdf")] });
    items = importReducer(items, { type: "added", items: [createImportItem("b", "b.pdf")] });
    expect(items.map((item) => item.id)).toEqual(["b", "a"]);

    items = importReducer(items, { type: "job_updated", id: "a", job: job({ status: "succeeded" }) });
    items = importReducer(items, { type: "failed", id: "b", message: "Sin red" });
    expect(items.map((item) => item.phase)).toEqual(["request_failed", "succeeded"]);

    items = importReducer(items, { type: "added", items: [createImportItem("c", "c.pdf")] });
    items = importReducer(items, { type: "finished_cleared" });
    expect(items.map((item) => item.id)).toEqual(["c"]);
  });
});

describe("describeItem", () => {
  it("muestra el mensaje recibido cuando falla la solicitud", () => {
    const item = { ...createImportItem("a", "a.pdf"), phase: "request_failed" as const, errorMessage: "Sin red" };
    expect(describeItem(item)).toBe("Sin red");
  });
});

describe("partitionPdfFiles", () => {
  it("acepta PDF por tipo o extensión y separa el resto", () => {
    const byType = new File([""], "acta", { type: "application/pdf" });
    const byExt = new File([""], "ACTA.PDF");
    const other = new File([""], "foto.png", { type: "image/png" });
    const result = partitionPdfFiles([byType, byExt, other]);
    expect(result.accepted).toEqual([byType, byExt]);
    expect(result.rejected).toEqual([other]);
  });
});
