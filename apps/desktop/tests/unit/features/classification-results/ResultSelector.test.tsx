import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ResultSelector } from "@/features/classification-results";
import { createFakeClassificationRun } from "../../../support/fakeBackend";

const base = createFakeClassificationRun().results[0];
if (!base) throw new Error("Fixture incompleta");
const results = Array.from({ length: 383 }, (_, index) => ({ ...base, id: index + 1, product_id: index + 1 }));

describe("ResultSelector pagination", () => {
  it("shows ten products, navigates both ways and preserves selection", async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    const { rerender } = render(<ResultSelector results={results} activeResultId={1} onSelect={onSelect} />);
    expect(within(screen.getByRole("list")).getAllByRole("button")).toHaveLength(10);
    expect(screen.getByLabelText("Página anterior")).toBeDisabled();
    await user.click(screen.getByLabelText("Página siguiente"));
    expect(screen.getByRole("status")).toHaveTextContent("Página 2 de 39");
    const first = within(screen.getByRole("list")).getAllByRole("button")[0];
    if (!first) throw new Error("Página sin productos");
    await user.click(first);
    expect(onSelect).toHaveBeenCalledWith(11);
    rerender(<ResultSelector results={results} activeResultId={11} onSelect={onSelect} />);
    await user.click(screen.getByLabelText("Página anterior"));
    await user.click(screen.getByLabelText("Página siguiente"));
    expect(within(screen.getByRole("list")).getAllByRole("button")[0]).toHaveAttribute("aria-pressed", "true");
  });

  it("handles the last partial page and a shorter refreshed list", () => {
    const { rerender } = render(<ResultSelector results={results} activeResultId={383} onSelect={vi.fn()} />);
    expect(within(screen.getByRole("list")).getAllByRole("button")).toHaveLength(3);
    expect(screen.getByLabelText("Página siguiente")).toBeDisabled();
    expect(screen.getByRole("button", { name: /Producto 383/ })).toBeInTheDocument();
    rerender(<ResultSelector results={results.slice(0, 10)} activeResultId={1} onSelect={vi.fn()} />);
    expect(screen.queryByRole("navigation")).not.toBeInTheDocument();
    expect(within(screen.getByRole("list")).getAllByRole("button")).toHaveLength(10);
  });
});
