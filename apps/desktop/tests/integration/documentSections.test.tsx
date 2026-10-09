import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { App } from "@/app";
import { createFakeBackend, createFakeCertificate, createFakeClassificationRun, envelope, healthyRoutes } from "../support/fakeBackend";

describe("Secciones del documento", () => {
  it("despliega dentro de la tabla sólo los datos del rollo seleccionado", async () => {
    const base = createFakeCertificate();
    const heat = base.heats[0];
    const product = base.products[0];
    const chemical = base.chemical_compositions[0];
    const observation = base.observations[0];
    if (!heat || !product || !chemical || !observation) throw new Error("Fixture incompleta");
    const certificate = createFakeCertificate({
      heats: [heat, { ...heat, id: 2, heat_no: "SEGUNDA" }],
      products: [product, { ...product, id: 2, heat_id: heat.id, product_identifier: "ROLLO-SEGUNDO" }],
      chemical_compositions: [...base.chemical_compositions, { ...chemical, id: 3, heat_id: heat.id, product_id: 2, element: "Ti", percentage: "0.77" }],
      observations: [...base.observations, { ...observation, id: 3, heat_id: heat.id, product_id: 2, normalized_value: "777", raw_value: 777 }],
    });
    const backend = createFakeBackend({ ...healthyRoutes,
      "GET /api/v1/certificates": () => envelope([certificate]),
      "GET /api/v1/certificates/42": () => envelope(certificate),
      "GET /api/v1/certificates/42/classification-runs": () => envelope([{ id: 101 }]),
      "GET /api/v1/classification-runs/101": () => envelope(createFakeClassificationRun()),
    });
    const user = userEvent.setup();
    render(<App apiClient={backend.client} />);
    await user.click(screen.getByRole("button", { name: "Historial de actas" }));
    await user.click(await screen.findByRole("button", { name: "Abrir acta" }));
    await screen.findByRole("button", { name: "Colada: SEGUNDA" });
    await user.click(screen.getByRole("button", { name: "Ver detalle: PL-001" }));
    expect(screen.getByRole("button", { name: "Extraído" })).toHaveAttribute("aria-current", "true");
    const firstPanel = screen.getByRole("region", { name: "Ver detalle: PL-001" });
    expect(firstPanel.closest("table")).toBe(screen.getByRole("table", { name: "Coladas" }));
    expect(within(firstPanel).getByText("Mn", { exact: true })).toBeInTheDocument();
    expect(within(firstPanel).queryByText("Ti", { exact: true })).not.toBeInTheDocument();
    await user.click(screen.getByRole("row", { name: /ROLLO-SEGUNDO/ }));
    expect(screen.queryByRole("region", { name: "Ver detalle: PL-001" })).not.toBeInTheDocument();
    const panel = screen.getByRole("region", { name: "Ver detalle: ROLLO-SEGUNDO" });
    expect(panel.closest("tr")?.previousElementSibling).toBe(screen.getByRole("row", { name: /ROLLO-SEGUNDO.*Cerrar detalle/ }));
    expect(within(panel).getByText("Ti", { exact: true })).toBeInTheDocument();
    expect(within(panel).queryByText("Mn", { exact: true })).not.toBeInTheDocument();
    expect(within(panel).getAllByText(/777/).length).toBeGreaterThan(0);
    expect(within(panel).queryByText("310 MPa", { exact: true })).not.toBeInTheDocument();
    await user.keyboard("{Tab}");
    await user.click(screen.getByRole("button", { name: "Ver detalle: ROLLO-SEGUNDO" }));
    expect(screen.queryByRole("heading", { name: "Composición Química (%)" })).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Ver detalle: PL-001" }));
    expect(screen.getByRole("region", { name: "Ver detalle: PL-001" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Colada: SEGUNDA" }));
    expect(screen.queryByRole("region", { name: "Ver detalle: PL-001" })).not.toBeInTheDocument();

  });
  it("selecciona una colada y recorre cuatro secciones sin historial ni campos de dictamen", async () => {
    const certificate = createFakeCertificate();
    const run = createFakeClassificationRun();
    const backend = createFakeBackend({ ...healthyRoutes,
      "GET /api/v1/certificates": () => envelope([certificate]),
      "GET /api/v1/certificates/42": () => envelope(certificate),
      "GET /api/v1/certificates/42/classification-runs": () => envelope([{ id: 101 }]),
      "GET /api/v1/classification-runs/101": () => envelope(run),
    });
    const user = userEvent.setup();
    render(<App apiClient={backend.client} />);
    await user.click(await screen.findByRole("button", { name: "Historial de actas" }));
    await user.click(await screen.findByRole("button", { name: "Abrir acta" }));
    expect(await screen.findByRole("heading", { name: "Información General" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Composición Química (%)" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Colada: C-9876" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("table", { name: "Coladas" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Extraído" }));
    expect(screen.queryByRole("heading", { name: "Composición Química (%)" })).not.toBeInTheDocument();
    await user.click(screen.getByRole("row", { name: /PL-001/ }));
    expect(screen.getByRole("heading", { name: "Composición Química (%)" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Ver detalle: PL-001" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Validación" }));
    expect(screen.getByRole("heading", { name: "Motor de Clasificación" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Justificación de la clasificación" })).not.toBeInTheDocument();
    expect(screen.getByRole("form", { name: "Captura manual de fracción y NICO" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Historial" })).not.toBeInTheDocument();
    expect(screen.queryByRole("contentinfo")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Dictamen de clasificación" }));
    const footer = within(screen.getByRole("contentinfo"));
    expect(footer.getByText("Pendiente de revisión")).toBeInTheDocument();
    expect(footer.queryByRole("textbox")).not.toBeInTheDocument();
    expect(backend.calls.some((call) => call.startsWith("POST"))).toBe(false);
  });
});
