import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { App } from "@/app";
import { es } from "@/lib/i18n";
import { createFakeBackend } from "../support/fakeBackend";

describe("Guía de clasificación", () => {
  it("permite leer con teclado sin backend y volver a la operación", async () => {
    render(<App apiClient={createFakeBackend({}).client} />);
    const user = userEvent.setup();
    const button = screen.getByRole("button", { name: es.classificationGuide.title });
    button.focus();
    await user.keyboard("{Enter}");
    expect(button).toHaveAttribute("aria-current", "page");
    const main = screen.getByRole("main");
    expect(within(main).getByRole("heading", { name: es.classificationGuide.title })).toBeVisible();
    expect(within(main).getAllByRole("listitem")).toHaveLength(es.classificationGuide.helpAreas.length + 6);
    expect(within(main).getByRole("heading", { name: es.classificationGuide.helpTitle })).toBeVisible();
    for (const area of es.classificationGuide.helpAreas) {
      expect(within(main).getByText(area.title, { selector: "summary span span" })).toBeVisible();
    }
    const helpArea = within(main).getByText(es.classificationGuide.helpAreas[0].title, { selector: "summary span span" }).closest("summary");
    if (!helpArea) throw new Error("Falta el control de la primera sección de ayuda");
    expect(within(main).getByText(es.classificationGuide.helpAreas[0].body)).not.toBeVisible();
    await user.click(helpArea);
    expect(within(main).getByText(es.classificationGuide.helpAreas[0].body)).toBeVisible();
    expect(within(main).getByText(es.classificationGuide.example)).toBeVisible();
    const step = within(main).getByText(es.classificationGuide.steps[0].title).closest("summary");
    expect(step).not.toBeNull();
    expect(within(main).getByText(es.classificationGuide.steps[0].body)).not.toBeVisible();
    if (!step) throw new Error("Falta el control del primer paso");
    step.focus();
    await user.click(step);
    expect(within(main).getByText(es.classificationGuide.steps[0].body)).toBeVisible();
    await user.click(step);
    expect(within(main).getByText(es.classificationGuide.steps[0].body)).not.toBeVisible();
    for (const link of es.classificationGuide.sectionLinks) {
      const anchor = within(main).getByRole("link", { name: link.label });
      expect(anchor).toHaveAttribute("href", `#${link.id}`);
      expect(document.getElementById(link.id)).toBeInTheDocument();
    }
    const exampleLink = within(main).getByRole("link", { name: "Ejemplo de un dato faltante" });
    await user.click(exampleLink);
    expect(exampleLink).toHaveAttribute("aria-current", "location");
    expect(within(main).getAllByRole("link").filter((link) => link.hasAttribute("aria-current"))).toHaveLength(1);
    await user.click(screen.getByRole("button", { name: es.nav.documents }));
    expect(screen.queryByRole("heading", { name: es.classificationGuide.title })).not.toBeInTheDocument();
    expect(await screen.findByRole("alert")).toBeVisible();
  });
});

