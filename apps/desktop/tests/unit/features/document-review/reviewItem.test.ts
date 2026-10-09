import { describe, expect, it } from "vitest";

import { reviewItemStatus, validateReprocessForm } from "@/features/document-review";
import type { DocumentReviewQueueItemDto } from "@/lib/api";

const base: DocumentReviewQueueItemDto = {
  source_file_name: null,
  revision_number: 1,
  active_job_id: null,
  can_reprocess: true,
  certificate_id: 42,
  document_id: 10,
  certificate_no: "CM-1",
  manufacturer: null,
  uploaded_at: "2026-10-08T00:00:00+00:00",
  document_status: "needs_review",
  approval_status: "needs_review",
  quality_score: 0.5,
  blocking_issues_count: 0,
  warning_issues_count: 0,
  issues_summary: [],
};

describe("reviewItemStatus", () => {
  it("un trabajo activo tiene prioridad", () => {
    expect(reviewItemStatus({ ...base, active_job_id: 7, blocking_issues_count: 2 })).toBe("loading");
  });
  it("con incidencias requiere revisión", () => {
    expect(reviewItemStatus({ ...base, warning_issues_count: 1 })).toBe("needs_review");
  });
  it("sin incidencias ni trabajos está correcto", () => {
    expect(reviewItemStatus(base)).toBe("success");
  });
});

describe("validateReprocessForm", () => {
  const messages = { personRequired: "persona", reasonRequired: "motivo" };
  it("exige persona (2) y motivo (3) sin contar espacios", () => {
    expect(validateReprocessForm(" a ", "  ab ", messages)).toEqual({ person: "persona", reason: "motivo" });
    expect(validateReprocessForm("Ana", "PDF nuevo", messages)).toEqual({});
  });
});
