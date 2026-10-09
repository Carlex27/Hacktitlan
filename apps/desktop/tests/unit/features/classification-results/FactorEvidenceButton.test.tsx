import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";
import type { EvidenceLinkDto } from "@/lib/api";
import { FactorEvidenceButton } from "@/features/classification-results/components/FactorEvidenceButton";

const link = (id: number, observation: number, field: string): EvidenceLinkDto => ({
  id, observation_id: observation, field_path: field, source_type: "observation", reference: {}, detail_url: `/api/v1/evidence/${id}`,
});

it("shows one direct button for repeated observation destinations", async () => {
  const open = vi.fn();
  render(<FactorEvidenceButton links={[link(1, 10, "width_mm"), link(2, 10, "width_mm")]} onOpen={open} />);
  expect(screen.getAllByRole("button", { name: "Ver evidencia" })).toHaveLength(1);
  await userEvent.setup().click(screen.getByRole("button", { name: "Ver evidencia" }));
  expect(open).toHaveBeenCalledWith(1);
  expect(screen.queryByRole("menu")).toBeNull();
});

it("keeps distinct evidence accessible from one keyboard operated button", async () => {
  const open = vi.fn();
  const user = userEvent.setup();
  render(<FactorEvidenceButton links={[link(1, 10, "width_mm"), link(2, 11, "thickness_mm")]} onOpen={open} />);
  expect(screen.getAllByRole("button", { name: "Ver evidencia" })).toHaveLength(1);
  await user.tab();
  await user.keyboard("{Enter}");
  expect(await screen.findByRole("menuitem", { name: "Ancho (mm)" })).toBeVisible();
  await user.keyboard("{ArrowDown}{Enter}");
  expect(open).toHaveBeenCalledWith(2);
});
