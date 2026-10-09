import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { App } from "@/app";
import { createFakeBackend, createFakeCertificate, envelope, errorEnvelope, healthyRoutes } from "../support/fakeBackend";

describe("Borrar el acta abierta", () => {
  it("borra sólo el acta seleccionada, sin cuerpo, y actualiza el historial", async () => {
    const certificate = createFakeCertificate();
    const other = { ...certificate, id: 43, document_id: 11, certificate_no: "OTRA-ACTA" };
    let deleted = false;
    let complete: (response: Response) => void = () => { throw new Error("No comenzó el borrado"); };
    let body: unknown = "not-called";
    const backend = createFakeBackend({ ...healthyRoutes,
      "GET /api/v1/certificates": () => envelope(deleted ? [other] : [certificate, other]),
      "GET /api/v1/certificates/42": () => envelope(certificate),
      "GET /api/v1/certificates/42/classification-runs": () => envelope([]),
      "DELETE /api/v1/certificates/42": (init) => {
        body = init?.body;
        return new Promise<Response>((resolve) => { complete = resolve; });
      },
    });
    render(<App apiClient={backend.client} />);
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: "Historial de actas" }));
    const [open] = await screen.findAllByRole("button", { name: "Abrir acta" });
    if (!open) throw new Error("No se encontró el acta");
    await user.click(open);
    const button = await screen.findByRole("button", { name: "Borrar" });
    button.focus();
    await user.keyboard("{Enter}");
    expect(await screen.findByRole("button", { name: "Borrando…" })).toBeDisabled();
    expect(body).toBeUndefined();
    deleted = true;
    complete(envelope({ certificate_id: 42, document_id: 10, deleted: true }));
    expect(await screen.findByText("Acta borrada correctamente.")).toBeInTheDocument();
    expect(await screen.findByText("OTRA-ACTA")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Borrar" })).not.toBeInTheDocument();
    expect(backend.calls.filter((call) => call.startsWith("DELETE"))).toEqual(["DELETE /api/v1/certificates/42"]);
  });

  it.each([403, 409, 500])("muestra el error %s y permite reintentar sin cerrar el acta", async (status) => {
    const backend = createFakeBackend({ ...healthyRoutes,
      "GET /api/v1/certificates": () => envelope([createFakeCertificate()]),
      "GET /api/v1/certificates/42": () => envelope(createFakeCertificate()),
      "GET /api/v1/certificates/42/classification-runs": () => envelope([]),
      "DELETE /api/v1/certificates/42": () => errorEnvelope("certificate_in_use", "El acta no se puede borrar", status),
    });
    render(<App apiClient={backend.client} />);
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: "Historial de actas" }));
    await user.click(await screen.findByRole("button", { name: "Abrir acta" }));
    await user.click(await screen.findByRole("button", { name: "Borrar" }));
    expect(await screen.findByText("No se pudo borrar el acta")).toBeInTheDocument();
    await waitFor(() => expect(screen.getByRole("button", { name: "Borrar" })).toBeEnabled());
    expect(screen.getByRole("button", { name: "Generar clasificación" })).toBeInTheDocument();
    expect(screen.queryByText("Acta borrada correctamente.")).not.toBeInTheDocument();
  });
});
