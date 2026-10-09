import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { App } from "@/app";
import type { CertificateObservationDto } from "@/lib/api";
import { createFakeBackend, createFakeCertificate, createFakeClassificationRun, envelope, errorEnvelope, healthyRoutes } from "../support/fakeBackend";

export function verifiedObservation(id: number, status: "matches" | "discrepancy" | "not_verifiable" | "error"): CertificateObservationDto {
  const cited = status === "matches" || status === "discrepancy";
  return { id, product_id: 1, heat_id: 1, field_path: `composition_pct.${id === 1 ? "C" : id === 2 ? "Mn" : id === 3 ? "Si" : "P"}`,
    raw_value: "13", normalized_value: status === "matches" ? .0013 : .13, unit: "%", confidence: null,
    page_number: 1, bbox: null, source_text: "13", is_current: true, inherited: false, supersedes_id: null,
    verification: { status, model: "qwen3.5:4b", raw_value: cited ? "13" : null, normalized_value: cited ? .0013 : null,
      unit: cited ? "%" : null, page_number: cited ? 1 : null, source_id: cited ? "t0r1c1" : null,
      source_text: cited ? "13" : null, header_id: cited ? "t0r0c1" : null, header_text: cited ? "C 10^-4" : null,
      bbox: null, header_bbox: null, error_code: status === "error" ? "TimeoutError" : null } };
}

describe("Verificación por campo", () => {
  it("shows all outcomes, opens PDF evidence, preserves values on error and accepts an audited correction", async () => {
    let certificate = createFakeCertificate({ observations: [verifiedObservation(1, "discrepancy"), verifiedObservation(2, "matches"),
      verifiedObservation(3, "not_verifiable"), verifiedObservation(4, "error")] });
    let request: unknown;
    let resolveCorrection: ((response: Response) => void) | undefined;
    let fail = true;
    const backend = createFakeBackend({ ...healthyRoutes,
      "GET /api/v1/certificates": () => envelope([certificate]),
      "GET /api/v1/certificates/42": () => envelope(certificate),
      "GET /api/v1/certificates/42/classification-runs": () => envelope([{ id: 101 }]),
      "GET /api/v1/classification-runs/101": () => envelope(createFakeClassificationRun()),
      "POST /api/v1/observations/1/corrections": (init) => {
        request = JSON.parse(String(init?.body));
        if (fail) { fail = false; return errorEnvelope("verification_unavailable", "La propuesta ya no está disponible", 409); }
        return new Promise<Response>((resolve) => { resolveCorrection = resolve; });
      },
    });
    const user = userEvent.setup();
    render(<App apiClient={backend.client} />);
    await user.click(screen.getByRole("button", { name: "Historial de actas" }));
    await user.click(await screen.findByRole("button", { name: "Abrir acta" }));
    await screen.findByRole("heading", { name: "Información General" });
    await user.click(await screen.findByRole("button", { name: "Extraído" }));
    await user.click(await screen.findByRole("button", { name: "Ver detalle: PL-001" }));
    await user.click(await screen.findByText("Datos extraídos principales"));
    expect(screen.getByText("Discrepancia · requiere revisión")).toBeInTheDocument();
    expect(screen.getByText("Coincide con la evidencia")).toBeInTheDocument();
    expect(screen.getByText("No verificable")).toBeInTheDocument();
    expect(screen.getByText("No pudo verificarse")).toBeInTheDocument();
    const row = screen.getByRole("row", { name: /Composición química · C/ });
    expect(within(row).getByText("0.13 %")).toBeInTheDocument();
    expect(within(row).getByText("Encabezado: C 10^-4")).toBeInTheDocument();
    await user.click(within(row).getByRole("button", { name: "Ver evidencia · Página 1" }));
    expect(await screen.findByTitle("Acta CM-2024-001")).toHaveAttribute("src", expect.stringContaining("#page=1"));
    await user.click(within(row).getByText("Revisar propuesta"));
    await user.type(screen.getByLabelText("Persona que revisa"), "Ana");
    await user.type(screen.getByLabelText("Motivo de la corrección"), "Revisé la celda y la escala");
    await user.click(screen.getByRole("button", { name: "Aceptar corrección" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("La propuesta ya no está disponible");
    expect(within(row).getByText("0.13 %")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Aceptar corrección" }));
    expect(await screen.findByRole("button", { name: "Guardando corrección…" })).toBeDisabled();
    expect(request).toEqual({ person_name: "Ana", reason: "Revisé la celda y la escala", accept_verification: true });
    certificate = { ...certificate, observations: certificate.observations.map((o) => o.id === 1
      ? { ...o, id: 5, supersedes_id: 1, normalized_value: .0013, verification: null } : o) };
    await waitFor(() => expect(resolveCorrection).toBeDefined());
    resolveCorrection?.(envelope({ observation_id: 5, supersedes_id: 1 }));
    expect(await screen.findByText(/Corrección guardada/)).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByText("Discrepancia · requiere revisión")).toBeNull());
    expect(screen.getByText("Corrección aceptada en revisión")).toBeInTheDocument();
    expect(certificate.observations[0]?.raw_value).toBe("13");
  });
});
