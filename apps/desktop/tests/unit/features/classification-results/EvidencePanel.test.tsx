import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { EvidencePanel } from "@/features/classification-results";
import type { ObservationEvidenceDto, RuleSourceEvidenceDto } from "@/lib/api";

describe("EvidencePanel", () => {
  it("renderiza información de evidencia de observación y permite ir a la página", async () => {
    const user = userEvent.setup();
    const onGoToPage = vi.fn();
    const onClose = vi.fn();

    const evidence: ObservationEvidenceDto = {
      id: 99,
      decision_step_id: 10,
      candidate_factor_id: null,
      source_type: "observation",
      field_path: "dimensions.thickness_mm",
      observation: {
        id: 1,
        raw_value: "12.70",
        normalized_value: "12.70",
        unit: "mm",
        confidence: 0.98,
        source_text: "Espesor: 12.70 mm",
      },
      document: {
        id: 5,
        file_url: "/api/v1/documents/5/file",
      },
      focus: {
        page_number: 2,
        bbox: [10, 20, 30, 40],
        can_focus_region: true,
        fallback: null,
      },
    };

    render(<EvidencePanel evidence={evidence} onClose={onClose} onGoToPage={onGoToPage} />);

    expect(screen.getByText(/Detalle de Evidencia\s+#99/)).toBeInTheDocument();
    expect(screen.getByText("dimensions.thickness_mm")).toBeInTheDocument();
    expect(screen.getByText("Espesor: 12.70 mm")).toBeInTheDocument();
    expect(screen.getByText(/Página del PDF/)).toBeInTheDocument();

    const goToPageBtn = screen.getByRole("button", { name: /ir a la página 2/i });
    await user.click(goToPageBtn);
    expect(onGoToPage).toHaveBeenCalledWith(2);

    const closeBtn = screen.getByTitle("Cerrar");
    await user.click(closeBtn);
    expect(onClose).toHaveBeenCalled();
  });

  it("renderiza evidencia de regla de clasificación (rule_source)", () => {
    const evidence: RuleSourceEvidenceDto = {
      id: 100,
      decision_step_id: 12,
      candidate_factor_id: null,
      source_type: "rule_source",
      reference: {
        rule_code: "RULE_LIGIE_7208",
        title: "Regla General de Interpretación 1",
      },
    };

    render(<EvidencePanel evidence={evidence} onClose={() => {}} />);
    expect(screen.getByText(/Detalle de Evidencia\s+#100/)).toBeInTheDocument();
    expect(screen.getAllByText("Texto normativo / regla")[0]).toBeInTheDocument();
    expect(screen.getByText("RULE_LIGIE_7208")).toBeInTheDocument();
  });
});
