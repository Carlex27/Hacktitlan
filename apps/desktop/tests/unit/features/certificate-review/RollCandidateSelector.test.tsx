import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { RollCandidateSelector } from "@/features/certificate-review/components/RollCandidateSelector";

const candidates = [
  { id: 1, fraction: "72255091", nico: "99", description: "Los demás.", support_level: "conditional" as const },
  { id: 2, fraction: "72255091", nico: "02", description: "Descripción extensa que debe mostrarse completa para revisar la alternativa.", support_level: "conditional" as const },
];

describe("RollCandidateSelector", () => {
  it("abre con teclado, muestra descripciones completas y entrega el candidato elegido", async () => {
    const onSelect = vi.fn();
    const current = candidates[0];
    if (!current) throw new Error("Missing fixture");
    render(<RollCandidateSelector candidates={candidates} current={current} identifier="R-1" disabled={false} onSelect={onSelect} />);
    const user = userEvent.setup();
    await user.tab();
    await user.keyboard("{Enter}");
    expect(screen.getByText(candidates[1]?.description ?? "")).toBeVisible();
    expect(screen.getByRole("menuitemradio", { name: /NICO 99/ })).toHaveAttribute("aria-checked", "true");
    await user.keyboard("{ArrowDown}{Enter}");
    expect(onSelect).toHaveBeenCalledWith(2);
    expect(screen.queryByRole("menu")).not.toBeInTheDocument();
  });
  it("no abre si la revisión está deshabilitada", () => {
    const current = candidates[0];
    if (!current) throw new Error("Missing fixture");
    render(<RollCandidateSelector candidates={candidates} current={current} identifier="R-1" disabled onSelect={vi.fn()} />);
    expect(screen.getByRole("button", { name: "NICO y alternativas: R-1" })).toBeDisabled();
  });
});
