import { describe, expect, it } from "vitest";
import { completedImportKey } from "@/features/certificate-import";
import { createImportItem } from "@/features/certificate-import/model/importItem";

describe("completedImportKey", () => {
  it("cambia por cada extracción terminada, no por su progreso ni por errores", () => {
    const pending = createImportItem("a", "acta.pdf");
    expect(completedImportKey([pending])).toBe("");
    expect(completedImportKey([{ ...pending, phase: "running", progress: 80 }])).toBe("");
    expect(completedImportKey([{ ...pending, phase: "failed" }])).toBe("");
    expect(completedImportKey([{ ...pending, phase: "succeeded" }])).toBe("a");
    expect(completedImportKey([{ ...pending, phase: "succeeded" }, { ...pending, id: "b", phase: "needs_review" }])).toBe("a,b");
  });
});
