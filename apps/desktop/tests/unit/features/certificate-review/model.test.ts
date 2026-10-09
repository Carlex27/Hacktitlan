import { describe, expect, it } from "vitest";

import type {
  CertificateChemicalCompositionDto,
  CertificateObservationDto,
} from "@/lib/api";
import {
  extractMechanicalProperties,
  formatChemicalCompositions,
  formatValueWithUnit,
} from "@/features/certificate-review/model";

describe("certificateReviewModel", () => {
  describe("formatValueWithUnit", () => {
    it("devuelve '—' para valores null o undefined sin convertirlos a cero", () => {
      expect(formatValueWithUnit(null, "MPa")).toBe("—");
      expect(formatValueWithUnit(undefined, "kg")).toBe("—");
    });

    it("conserva cadenas decimales exactas sin perder precisión ni parsear a number", () => {
      expect(formatValueWithUnit("0.00350", "%")).toBe("0.00350 %");
      expect(formatValueWithUnit("24580.750", "kg")).toBe("24580.750 kg");
      expect(formatValueWithUnit("12.0", null)).toBe("12.0");
    });

    it("soporta números sin alterar su representación", () => {
      expect(formatValueWithUnit(310, "MPa")).toBe("310 MPa");
      expect(formatValueWithUnit(0, "MPa")).toBe("0 MPa");
    });
  });

  describe("extractMechanicalProperties", () => {
    it("filtra únicamente observaciones con field_path de propiedades mecánicas", () => {
      const observations: CertificateObservationDto[] = [
        {
          id: 1,
          heat_id: 1,
          product_id: 1,
          field_path: "mechanical_properties.yield_strength",
          raw_value: 310,
          normalized_value: "310",
          unit: "MPa",
          confidence: 0.98,
          page_number: 1,
          bbox: null,
          source_text: "310 MPa",
          inherited: false,
          supersedes_id: null,
          is_current: true,
        },
        {
          id: 2,
          heat_id: 1,
          product_id: 1,
          field_path: "dimensions.thickness_mm",
          raw_value: 12,
          normalized_value: "12",
          unit: "mm",
          confidence: 0.99,
          page_number: 1,
          bbox: null,
          source_text: "12 mm",
          inherited: false,
          supersedes_id: null,
          is_current: true,
        },
      ];

      const result = extractMechanicalProperties(observations);
      expect(result).toHaveLength(1);
      expect(result[0]?.label).toBe("Límite elástico (Yield)");
      expect(result[0]?.value).toBe("310 MPa");
      expect(result[0]?.unit).toBe("MPa");
    });

    it("devuelve arreglo vacío cuando no hay observaciones mecánicas", () => {
      expect(extractMechanicalProperties([])).toEqual([]);
    });
  });

  describe("formatChemicalCompositions", () => {
    it("conserva porcentajes como string exacto y etiqueta adecuada", () => {
      const compositions: CertificateChemicalCompositionDto[] = [
        {
          id: 1,
          heat_id: 1,
          product_id: null,
          element: "C",
          raw_value: "0.180",
          percentage: "0.180",
          inherited: false,
          source_label: "Carbono",
        },
        {
          id: 2,
          heat_id: 1,
          product_id: null,
          element: "Si",
          raw_value: null,
          percentage: null,
          inherited: false,
          source_label: null,
        },
      ];

      const formatted = formatChemicalCompositions(compositions);
      expect(formatted).toHaveLength(2);
      expect(formatted[0]).toEqual({
        id: 1,
        element: "C",
        percentageDisplay: "0.180%",
        rawPercentage: "0.180",
        sourceLabel: "Carbono",
      });
      expect(formatted[1]).toEqual({
        id: 2,
        element: "Si",
        percentageDisplay: "—",
        rawPercentage: null,
        sourceLabel: null,
      });
    });
  });
});
