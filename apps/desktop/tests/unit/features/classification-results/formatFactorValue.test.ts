import { describe, expect, it } from "vitest";
import { formatFactorValue } from "@/features/classification-results/model";

describe("formatFactorValue", () => {
  it("presents chemistry with units and preserves numeric strings", () => {
    expect(formatFactorValue({ Ti: "0.068" }, "%")).toEqual(["Ti: 0.068 %"]);
  });
  it("labels properties and distinguishes missing data, false and zero", () => {
    expect(formatFactorValue({ width_mm: "991.0", rolling: "cold", coiled: true, coated: null, tool_steel: false, thickness_mm: 0 })).toEqual([
      "Ancho (mm): 991.0", "Laminación: Laminado en frío", "En rollo: Sí", "Con recubrimiento: Sin dato", "Acero para herramientas: No", "Espesor (mm): 0",
    ]);
  });
  it("preserves nested conditions, unknown fields and empty values without JSON syntax", () => {
    expect(formatFactorValue({ conditions: [{ field: "width_mm", operator: ">=", value: 600 }], new_field: [] })).toEqual([
      "Condiciones: Campo: width_mm", "Condiciones: Operador: >=", "Condiciones: Valor: 600", "new field: Sin dato",
    ]);
    expect(formatFactorValue({})).toEqual(["Sin dato"]);
  });
});
