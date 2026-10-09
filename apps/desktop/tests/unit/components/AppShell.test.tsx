import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { FileText, History } from "lucide-react";
import { describe, expect, it, vi } from "vitest";
import { AppShell } from "@/components/layout";

describe("AppShell navigation", () => {
  it("exposes the current section and supports keyboard navigation, skipping disabled entries", async () => {
    const onNavigate = vi.fn();
    render(<AppShell items={[
      { id: "import", label: "Carga y revisión", icon: FileText },
      { id: "disabled", label: "Reportes", icon: FileText, disabled: true },
      { id: "history", label: "Historial de actas", icon: History },
    ]} activeId="import" onNavigate={onNavigate} breadcrumbs={[]}>
      <p>Contenido</p>
    </AppShell>);
    const nav = within(screen.getByRole("navigation", { name: "Navegación principal" }));
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
