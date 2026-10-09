import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { FileText, History } from "lucide-react";
import { describe, expect, it, vi } from "vitest";
import { AppShell } from "@/components/layout";

describe("AppShell navigation", () => {
  it("shows document breadcrumbs without a back arrow and preserves the section return action", async () => {
    const onBack = vi.fn();
    render(<AppShell items={[]} activeId="import" onNavigate={vi.fn()} breadcrumbs={[
      { label: "Carga y revisión", onClick: onBack },
      { label: "Acta de Molino #17" },
    ]}><p>Contenido</p></AppShell>);
    const header = within(screen.getByRole("banner"));
    const breadcrumbs = within(header.getByRole("navigation", { name: "Migas de pan" }));
    expect(breadcrumbs.getByText("Acta de Molino #17")).toHaveAttribute("aria-current", "page");
    expect(breadcrumbs.getAllByRole("button")).toHaveLength(1);
    const user = userEvent.setup();
    await user.click(breadcrumbs.getByRole("button", { name: "Carga y revisión" }));
    expect(breadcrumbs.getByRole("button", { name: "Carga y revisión" })).toHaveFocus();
    await user.keyboard("{Enter}");
    expect(onBack).toHaveBeenCalledTimes(2);
  });

  it("exposes the current section and supports keyboard navigation, skipping disabled entries", async () => {
    const onNavigate = vi.fn();
    render(<AppShell items={[
      { id: "import", label: "Carga y revisión", icon: FileText },
      { id: "disabled", label: "Reportes", icon: FileText, disabled: true },
      { id: "history", label: "Historial de actas", icon: History },
    ]} activeId="import" onNavigate={onNavigate} breadcrumbs={[]}>
      <p>Contenido</p>
    </AppShell>);
    const header = within(screen.getByRole("banner"));
    const nav = within(header.getByRole("navigation", { name: "Navegación principal" }));
    expect(header.getByText("Clasificador LIGIE")).toBeInTheDocument();
    expect(screen.queryByRole("complementary")).not.toBeInTheDocument();
    const user = userEvent.setup();
    expect(nav.getByRole("button", { name: "Carga y revisión" })).toHaveAttribute("aria-current", "page");
    expect(nav.getByRole("button", { name: "Reportes" })).toBeDisabled();
    await user.tab();
    expect(nav.getByRole("button", { name: "Carga y revisión" })).toHaveFocus();
    await user.tab();
    expect(nav.getByRole("button", { name: "Historial de actas" })).toHaveFocus();
    await user.keyboard("{Enter}");
    expect(onNavigate).toHaveBeenCalledWith("history");
  });
});
