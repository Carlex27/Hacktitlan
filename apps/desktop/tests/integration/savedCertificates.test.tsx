import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { App } from "@/app";
import { createFakeBackend, createFakeCertificate, envelope, errorEnvelope, healthyRoutes } from "../support/fakeBackend";

describe("Actas guardadas", () => {
  it("muestra carga, vacío y orientación al buscar sin resultados", async () => {
    let finish: (response: Response) => void = () => { throw new Error("Consulta no iniciada"); };
    const backend = createFakeBackend({ ...healthyRoutes,
      "GET /api/v1/certificates": () => new Promise<Response>((resolve) => { finish = resolve; }),
      "GET /api/v1/certificates?certificate_no=INEXISTENTE": () => envelope([]),
    });
    render(<App apiClient={backend.client} />);
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: "Historial de actas" }));
    expect(await screen.findByText("Cargando actas guardadas")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Actualizar actas" })).toBeDisabled();
    finish(envelope([]));
    expect(await screen.findByText("No hay actas guardadas")).toBeInTheDocument();
    await user.type(screen.getByLabelText("Número de acta"), "INEXISTENTE");
    await user.click(screen.getByRole("button", { name: "Aplicar filtros" }));
    expect(await screen.findByText("Prueba con otros datos o limpia los filtros para consultar las actas guardadas.")).toBeInTheDocument();
  });
  it("recupera actas al recargar y abre sus datos sin volver a subir el PDF", async () => {
    const certificate = createFakeCertificate({ certificate_no: "ACTA-PERSISTIDA", manufacturer: "Molino persistido" });
    const backend = createFakeBackend({ ...healthyRoutes,
      "GET /api/v1/certificates": () => envelope([certificate]),
      "GET /api/v1/certificates/42": () => envelope(certificate),
      "GET /api/v1/certificates/42/classification-runs": () => envelope([]),
    });
    const first = render(<App apiClient={backend.client} />);
    await userEvent.setup().click(await screen.findByRole("button", { name: "Historial de actas" }));
    expect(await screen.findByText("ACTA-PERSISTIDA")).toBeInTheDocument();
    first.unmount();
    render(<App apiClient={backend.client} />);
    await userEvent.setup().click(await screen.findByRole("button", { name: "Historial de actas" }));
    const list = await screen.findByRole("list", { name: "Actas guardadas" });
    await userEvent.setup().click(within(list).getByRole("button", { name: "Abrir acta" }));
    expect(await screen.findByText("Molino persistido")).toBeInTheDocument();
    expect(backend.calls).not.toContain("POST /api/v1/documents");
  });

  it("permite reintentar un error y recorrer las páginas", async () => {
    let attempts = 0;
    const backend = createFakeBackend({ ...healthyRoutes,
      "GET /api/v1/certificates": () => {
        attempts += 1;
        return attempts === 1 ? errorEnvelope("internal_error", "Error de consulta", 500) :
          Response.json({ data: [createFakeCertificate({ certificate_no: "PRIMERA" })], meta: { next_cursor: "siguiente" }, error: null });
      },
      "GET /api/v1/certificates?cursor=siguiente": () => envelope([createFakeCertificate({ certificate_no: "SEGUNDA" })]),
    });
    render(<App apiClient={backend.client} />);
    await userEvent.setup().click(await screen.findByRole("button", { name: "Historial de actas" }));
    const user = userEvent.setup();
    await user.click(within(await screen.findByRole("alert")).getByRole("button", { name: "Reintentar" }));
    expect(await screen.findByText("PRIMERA")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Ver más actas" }));
    expect(await screen.findByText("SEGUNDA")).toBeInTheDocument();
  });
});
