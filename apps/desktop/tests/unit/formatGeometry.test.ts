import { describe, expect, it } from "vitest";
import { regionFromPoints, relativeBox, validRegion } from "@/features/certificate-formats/model/geometry";
import { emptyMapping } from "@/features/certificate-formats/model/mappings";
import { previewRows } from "@/features/certificate-formats/model/previewRows";

describe("Editor de zonas", () => {
  it("ordena el arrastre inverso, limita coordenadas y rechaza área cero", () => {
    expect(regionFromPoints({ x: 1.1, y: .7 }, { x: -.1, y: .2 })).toEqual({ x0: 0, top: .2, x1: 1, bottom: .7 });
    expect(regionFromPoints({ x: .2, y: .2 }, { x: .2, y: .8 })).toBeNull();
    expect(validRegion({ x0: NaN, top: 0, x1: 1, bottom: 1 })).toBe(false);
  });
  it("convierte coordenadas del layout independientemente del zoom", () => {
    expect(relativeBox({ x0: 10, top: 40, x1: 50, bottom: 100 }, { page_number: 1, width: 100, height: 200,
      rotation: 90, source: "ocr", blocks: [], tables: [] })).toEqual({ x0: .1, top: .2, x1: .5, bottom: .5 });
    expect(emptyMapping("chemistry")).toMatchObject({ unit: "%", exponent: 0, element: "C" });
  });
  it("presenta ceros y desconocidos sin convertirlos", () => {
    const rows = previewRows({ status: "success", diagnostics: [], certificate: { products: [{ product_id: "R1", thickness_mm: 0, width_mm: null }] },
      evidence: [{ field: "thickness_mm", raw_value: "0", page_number: 1 }, { field: "width_mm", raw_value: null, page_number: 1 }] });
    expect(rows[0]).toMatchObject({ original: "0", normalized: 0 });
    expect(rows[1]).toMatchObject({ original: null, normalized: null });
  });
});
