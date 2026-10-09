import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { CertificateObservationDto } from "@/lib/api";
import { primaryObservations, displayObservationValue, verifiedChemicalObservations } from "@/features/certificate-review/model";
import { ExtractedObservations } from "@/features/certificate-review/components/ExtractedObservations";

function observation(id: number, field_path: string, value: CertificateObservationDto["raw_value"] = null): CertificateObservationDto {
  return { id, field_path, raw_value: value, normalized_value: value, heat_id: null, product_id: null,
    unit: null, confidence: null, page_number: null, bbox: null, source_text: null,
    inherited: false, supersedes_id: null, is_current: true };
}

describe("Datos extraídos principales", () => {
  it("includes chemical corrections for review without duplicating unverified chemistry", () => {
    const rows = verifiedChemicalObservations([
      observation(1, "composition_pct.C", .13),
      { ...observation(2, "composition_pct.Ti", .1), supersedes_id: 1 },
      { ...observation(3, "composition_pct.P", .01), supersedes_id: 2, is_current: false },
    ]);
    expect(rows.map((row) => row.label)).toEqual(["Composición química · Ti"]);
  });
  it("keeps current technical fields, excluding chemistry and internal metadata", () => {
    const rows = primaryObservations([
      observation(1, "width_mm", 991), observation(2, "evidence", { page: 1 }),
      observation(3, "composition_pct.Ti", "0.068"), observation(4, "internal_notes", "internal"),
      { ...observation(5, "width_mm", 900), is_current: false },
    ]);
    expect(rows.map((row) => row.label)).toEqual(["Ancho"]);
    expect(rows[0]?.raw_value).toBe(991);
  });
  it("renders only field, original and normalized values", () => {
    render(<ExtractedObservations observations={[
      { ...observation(1, "width_mm", "991.0"), unit: "mm", source_text: "WIDTH 991", page_number: 1 },
      observation(2, "evidence", { page: 1 }), observation(3, "rolling", "cold"),
      observation(4, "composition_pct.C", "0.18"),
    ]} />);
    expect(screen.getByText("Ancho")).toBeInTheDocument();
    expect(screen.getByText("991.0 mm")).toBeInTheDocument();
    expect(screen.getAllByRole("columnheader", { hidden: true }).map((header) => header.textContent))
      .toEqual(["Campo", "Valor original", "Valor normalizado"]);
    expect(screen.queryByText("WIDTH 991 · Página 1")).toBeNull();
    expect(screen.getAllByText("Laminado en frío")).toHaveLength(2);
    expect(screen.queryByText("evidence")).toBeNull();
    expect(screen.queryByText(/Composición química/)).toBeNull();
    expect(screen.queryByText("Sin verificación local")).toBeNull();
  });
  it("shows an explicit empty state when only internal data exists", () => {
    render(<ExtractedObservations observations={[observation(1, "evidence")]} />);
    expect(screen.getByText("No hay datos principales extraídos disponibles.")).toBeInTheDocument();
  });
  it("distinguishes missing values, false and zero", () => {
    expect(displayObservationValue(null)).toBe("Sin dato");
    expect(displayObservationValue(false)).toBe("No");
    expect(displayObservationValue(0)).toBe("0");
    expect(displayObservationValue(["cold", true])).toBe("Laminado en frío; Sí");
  });
});
