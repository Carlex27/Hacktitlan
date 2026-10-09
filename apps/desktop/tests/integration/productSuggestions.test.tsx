import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { App } from "@/app";
import { createFakeBackend, createFakeCertificate, createFakeClassificationRun, envelope, healthyRoutes } from "../support/fakeBackend";

describe("Sugerencias junto a los rollos", () => {
  it("muestra la colada y los códigos del producto correspondiente sin visor PDF izquierdo", async () => {
    const base = createFakeCertificate();
    const product = base.products[0];
    const result = createFakeClassificationRun().results[0];
    if (!product || !result || !result.candidates[0]) throw new Error("Fixture incompleta");
    const certificate = createFakeCertificate({ products: [product,
      { ...product, id: 2, product_identifier: "ROLLO-002" }] });
    const run = createFakeClassificationRun({ results: [result, {
      ...result, id: 202, product_id: 2, current_selection: null, selections: [], outcome: "needs_review", fraction: null, nico: null,
      candidates: [{ ...result.candidates[0], id: 999, fraction: "72255091", nico: "08", support_level: "conditional" }],
    }] });
    const backend = createFakeBackend({ ...healthyRoutes,
      "GET /api/v1/certificates": () => envelope([certificate]),
      "GET /api/v1/certificates/42": () => envelope(certificate),
      "GET /api/v1/certificates/42/classification-runs": () => envelope([{ id: 101 }]),
      "GET /api/v1/classification-runs/101": () => envelope(run),
    });
    render(<App apiClient={backend.client} />);
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: "Historial de actas" }));
    await user.click(await screen.findByRole("button", { name: "Abrir acta" }));
    await user.click(await screen.findByRole("button", { name: "Colada: C-9876" }));
    const first = await screen.findByRole("row", { name: /PL-001/ });
    const second = await screen.findByRole("row", { name: /ROLLO-002/ });
    expect(screen.getByRole("button", { name: "Colada: C-9876" })).toHaveAttribute("aria-pressed", "true");
    expect(second).toHaveTextContent("72255091");
    expect(second).toHaveTextContent("NICO 08");
    expect(second).toHaveTextContent("Requiere revisión");
    expect(within(first).queryByText("72255091")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Validación" }));
    await user.click(screen.getByRole("button", { name: /ROLLO-002/ }));
    expect(screen.getByRole("radio", { name: /72255091/ })).toBeChecked();
    expect(backend.calls.some((call) => call.includes("/select"))).toBe(false);
    expect(screen.queryByRole("region", { name: "Visor de documento" })).not.toBeInTheDocument();
    expect(backend.calls).not.toContain("GET /api/v1/documents/10/file");
  });
});
