import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { RunSelectionHistory } from "@/features/classification-results";
import { createFakeClassificationRun } from "../../../support/fakeBackend";

describe("RunSelectionHistory", () => {
  it("muestra un solo vacío si todos los productos carecen de selecciones", () => {
    const run = createFakeClassificationRun();
    const result = run.results[0];
    if (!result) throw new Error("Missing fixture result");
    render(<RunSelectionHistory run={{ ...run, results: [
      { ...result, selections: [] }, { ...result, id: 202, product_id: 2, selections: [] },
    ] }} />);
    expect(screen.getAllByText("No hay selecciones manuales previas registradas.")).toHaveLength(1);
  });
  it("conserva los grupos y su auditoría si algún producto tiene selecciones", () => {
    const run = createFakeClassificationRun();
    const result = run.results[0];
    if (!result) throw new Error("Missing fixture result");
    render(<RunSelectionHistory run={{ ...run, results: [result, { ...result, id: 202, product_id: 2, selections: [] }] }} />);
    expect(screen.getByText("María Pérez")).toBeInTheDocument();
    expect(screen.getByText("No hay selecciones manuales previas registradas.")).toBeInTheDocument();
    expect(screen.getAllByRole("heading", { level: 5 })).toHaveLength(2);
  });
});
