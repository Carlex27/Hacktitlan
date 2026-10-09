import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { DatePicker } from "@/components/ui";
import { dateValue, monthDays, parseDate } from "@/components/ui/date-picker-model";

describe("DatePicker", () => {
  it("conserva fechas y calcula febrero bisiesto con semanas desde lunes", () => {
    expect(dateValue(parseDate("2024-02-29"))).toBe("2024-02-29");
    const days = monthDays(parseDate("2024-02-01"));
    expect(days.slice(0, 3)).toEqual([null, null, null]);
    expect(days.filter(Boolean)).toHaveLength(29);
  });

  it("selecciona con flechas, respeta límites y devuelve ISO", async () => {
    const onChange = vi.fn();
    render(<DatePicker id="date" label="Hasta" value="2026-10-09" min="2026-10-09" onChange={onChange} />);
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /^Hasta:/ }));
    expect(screen.getByRole("button", { name: "jueves, 8 de octubre de 2026" })).toBeDisabled();
    await user.keyboard("{ArrowRight}{Enter}");
    expect(onChange).toHaveBeenCalledWith("2026-10-10");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("cambia de mes y permite quitar la fecha", async () => {
    const onChange = vi.fn();
    render(<DatePicker id="date" label="Desde" value="2026-10-31" onChange={onChange} />);
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /^Desde:/ }));
    await user.keyboard("{ArrowRight}{Enter}");
    expect(onChange).toHaveBeenCalledWith("2026-11-01");
    await user.click(screen.getByRole("button", { name: /^Desde:/ }));
    await user.click(screen.getByRole("button", { name: "Quitar fecha" }));
    expect(onChange).toHaveBeenCalledWith("");
  });
});
