import { describe, expect, it } from "vitest";
import { activeSectionIndex } from "@/features/classification-guide/activeSection";

describe("Sección visible de la guía", () => {
  it("mantiene la primera antes del recorrido y cambia al cruzar la línea de lectura", () => {
    expect(activeSectionIndex([200, 500, 800], 120, false)).toBe(0);
    expect(activeSectionIndex([-400, 100, 400], 120, false)).toBe(1);
    expect(activeSectionIndex([-400, 121, 400], 120, false)).toBe(0);
  });
  it("marca la última al final aunque sea demasiado corta para alcanzar la línea", () => {
    expect(activeSectionIndex([-800, -200, 300], 120, true)).toBe(2);
  });
});
