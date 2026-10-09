import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { App } from "@/app";
import type { CertificateObservationDto } from "@/lib/api";
import { createFakeBackend, createFakeCertificate, createFakeClassificationRun, envelope, healthyRoutes } from "../support/fakeBackend";

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

describe("Datos extraídos sin verificación local", () => {
  it("opens an acta and roll with only the three data columns even when verification exists", async () => {
    const certificate = createFakeCertificate({ observations: [
      { ...verifiedObservation(1, "discrepancy"), field_path: "width_mm", raw_value: "991", normalized_value: 991, unit: "mm" },
    ] });
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
    await screen.findByRole("heading", { name: "Información General" });
    await user.click(await screen.findByRole("button", { name: "Extraído" }));
    await user.click(await screen.findByRole("button", { name: "Ver detalle: PL-001" }));
    await user.click(await screen.findByText("Datos extraídos principales"));
    const table = screen.getByRole("table", { name: "", hidden: false });
    expect(within(table).getAllByRole("columnheader").map((header) => header.textContent))
      .toEqual(["Campo", "Valor original", "Valor normalizado"]);
    expect(within(table).getByText("991")).toBeInTheDocument();
    expect(within(table).getByText("991 mm")).toBeInTheDocument();
    expect(screen.queryByText("Verificación local")).toBeNull();
    expect(screen.queryByText("Revisar propuesta")).toBeNull();
  });
});
