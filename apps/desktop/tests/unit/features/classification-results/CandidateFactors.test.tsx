import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it } from "vitest";
import { CandidateFactors } from "@/features/classification-results/components/CandidateFactors";

it("opens readable factor data without JSON syntax", async () => {
  const { container } = render(<CandidateFactors candidate={{
    id: 1, rank: 1, fraction: "72255091", nico: "99", description: null,
    support_level: "conditional", details: {}, detail_url: "",
    factors: [{ id: 1, sequence: 1, rule_code: "alloy", outcome: "matched", operator: null,
      expected: { Ti: "0.05" }, observed: { Ti: "0.068", coated: null }, unit: "%",
      explanation: "Umbral de acero aleado", required_for_selection: true,
      evidence_links: [],
    }],
  }} />);
  await userEvent.setup().click(screen.getByText("Umbral de acero aleado · Cumple"));
  expect(container.querySelector("details")).toHaveAttribute("open");
  expect(screen.getByText("Ti: 0.05 %")).toBeVisible();
  expect(screen.getByText("Condición esperada")).toBeVisible();
  expect(screen.getByText("Ti: 0.068 %")).toBeVisible();
  expect(screen.getByText("Con recubrimiento: Sin dato")).toBeVisible();
  for (const delimiter of ["{", "}", "[", "]"]) expect(container.textContent).not.toContain(delimiter);
});
