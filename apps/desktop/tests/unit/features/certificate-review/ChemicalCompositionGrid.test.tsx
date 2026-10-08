import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ChemicalCompositionGrid } from "@/features/certificate-review";
import type { CertificateChemicalCompositionDto } from "@/lib/api";

describe("ChemicalCompositionGrid", () => {
  it("muestra estado vacío cuando no hay composiciones químicas", () => {
    render(<ChemicalCompositionGrid compositions={[]} />);
    expect(screen.getByText("Sin composición química")).toBeInTheDocument();
  });

  it("renderiza elementos y porcentajes en formato exacto sin convertir a número", () => {
    const compositions: CertificateChemicalCompositionDto[] = [
      {
        id: 1,
        heat_id: 1,
        product_id: null,
        element: "C",
        raw_value: "0.0450",
        percentage: "0.0450",
        inherited: false,
        source_label: "Carbono",
      },
      {
        id: 2,
        heat_id: 1,
        product_id: null,
        element: "Mn",
        raw_value: "1.200",
        percentage: "1.200",
        inherited: false,
        source_label: "Manganeso",
      },
    ];

    render(<ChemicalCompositionGrid compositions={compositions} />);
    expect(screen.getByText("C")).toBeInTheDocument();
    expect(screen.getByText("0.0450%")).toBeInTheDocument();
    expect(screen.getByText("Mn")).toBeInTheDocument();
    expect(screen.getByText("1.200%")).toBeInTheDocument();
  });
});
