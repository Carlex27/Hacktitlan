import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import userEvent from "@testing-library/user-event";
import { ProductTariffSuggestions } from "@/features/classification-results";

describe("ProductTariffSuggestions", () => {
  it("muestra carga y luego ausencia explícita de sugerencias", () => {
    const view = render(<ProductTariffSuggestions result={undefined} isLoading error={null} />);
    expect(screen.getByRole("status")).toHaveTextContent("Cargando sugerencias");
    view.rerender(<ProductTariffSuggestions result={undefined} isLoading={false} error={null} />);
    expect(screen.getByText("Sin sugerencias de clasificación para este rollo")).toBeInTheDocument();
  });

  it("muestra el error de consulta y permite reintentar", async () => {
    const retry = vi.fn();
    render(<ProductTariffSuggestions result={undefined} isLoading={false} error={new Error("Sin conexión")} onRetry={retry} />);
    expect(screen.getByRole("alert")).toHaveTextContent("No se pudo cargar la clasificación");
    await userEvent.setup().click(screen.getByRole("button", { name: "Reintentar" }));
    expect(retry).toHaveBeenCalledOnce();
  });
});
