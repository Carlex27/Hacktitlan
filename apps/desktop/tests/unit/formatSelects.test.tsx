import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { MappingValueForm } from "@/features/certificate-formats/components/MappingValueForm";
import { TableMappingForm } from "@/features/certificate-formats/components/TableMappingForm";
import { emptyMapping } from "@/features/certificate-formats/model/mappings";

describe("Selectores del editor de formatos", () => {
  it("conserva unidad y separador decimal al seleccionar con teclado", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    const value = emptyMapping("thickness_mm");
    render(<MappingValueForm value={value} onChange={onChange} />);
    expect(document.querySelectorAll("select")).toHaveLength(0);
    await user.click(screen.getByRole("combobox", { name: "Unidad" }));
    await user.keyboard("{End}{Enter}");
    expect(onChange).toHaveBeenLastCalledWith({ ...value, unit: "m" });
    await user.click(screen.getByRole("combobox", { name: "Separador decimal" }));
    await user.click(screen.getByRole("option", { name: /^,$/ }));
    expect(onChange).toHaveBeenLastCalledWith({ ...value, decimal_separator: "," });
  });
  it("deshabilita también los selectores de columnas de una tabla bloqueada", () => {
    render(<TableMappingForm disabled table={{ page_number: 1, region: { x0: 0, top: 0, x1: 1, bottom: 1 }, role: "products", join_key: "product_id", header_row: 0,
      columns: [{ ...emptyMapping("thickness_mm"), header: "Thickness" }] }} onChange={vi.fn()} />);
    expect(screen.getAllByRole("combobox")).toHaveLength(5);
    for (const control of screen.getAllByRole("combobox")) expect(control).toBeDisabled();
    expect(document.querySelectorAll("select")).toHaveLength(0);
  });
});
