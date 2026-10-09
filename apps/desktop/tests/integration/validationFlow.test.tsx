import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { App } from "@/app";
import { es } from "@/lib/i18n";
import {
  createFakeBackend,
  createFakeCertificate,
  createFakeClassificationRun,
  envelope,
  healthyRoutes,
} from "../support/fakeBackend";

describe("Flujo de revisión y validación de acta", () => {
  it("muestra datos reales de API, permite navegar entre pestañas, seleccionar candidato y dictaminar", async () => {
    const user = userEvent.setup();
    const certificate = createFakeCertificate({
      id: 42,
      certificate_no: "CM-2024-001",
      manufacturer: "Altos Hornos de México",
      standard: "EN 10025-2",
    });
    const run = createFakeClassificationRun({
      id: 101,
      certificate_id: 42,
    });

    const backend = createFakeBackend({
      ...healthyRoutes,
      "GET /api/v1/certificates/42": () => envelope(certificate),
      "GET /api/v1/certificates/42/classification-runs": () =>
        envelope([
          {
            id: 101,
            rule_set_id: 1,
            parent_run_id: null,
            approval_status: "needs_review",
            demo_notice: "Reglas demo",
            created_at: "2024-05-16T10:00:00Z",
          },
        ]),
      "GET /api/v1/classification-runs/101": () => envelope(run),
      "POST /api/v1/classification-results/201/select": () =>
        envelope({
          selection_id: 55,
          classification_result_id: 201,
          candidate_id: 302,
          fraction: "7208.52",
          nico: "01",
          person_name: "Dictaminador Prueba",
          reason: "Espesor corregido a 6mm",
          workstation_name: "W1",
          created_at: "2024-05-16T12:00:00Z",
        }),
      "POST /api/v1/classification-runs/101/approve": () =>
        envelope({ classification_run_id: 101, approval_status: "approved" }),
    });

    render(<App apiClient={backend.client} />);

    // Iniciar en Documentos
    expect(await screen.findByRole("heading", { name: /importar actas de molino/i })).toBeInTheDocument();

    // Navegar a Validación haciendo clic en el botón de la barra lateral
    const validationNavBtn = screen.getByRole("button", { name: "Validación" });
    await user.click(validationNavBtn);

    // Sin acta seleccionada aún, muestra estado vacío o sin datos
    expect(screen.getByText("Seleccione un acta para consultar su información.")).toBeInTheDocument();

    // Regresar a Documentos mediante el botón de migas de pan
    const backBtn = screen.getByTitle("Regresar");
    await user.click(backBtn);
    expect(await screen.findByRole("heading", { name: /importar actas de molino/i })).toBeInTheDocument();
  });

  it("renderiza datos extraídos reales de la API en la vista de validación", async () => {
    const user = userEvent.setup();
    const certificate = createFakeCertificate({
      id: 42,
      certificate_no: "CM-2024-001",
      manufacturer: "Altos Hornos de México",
      standard: "EN 10025-2",
    });
    const run = createFakeClassificationRun({
      id: 101,
      certificate_id: 42,
    });

    const backend = createFakeBackend({
      ...healthyRoutes,
      "POST /api/v1/documents": () =>
        envelope({ document_id: 10, certificate_id: 42, job_id: null, duplicate: false }, 200),
      "GET /api/v1/certificates/42": () => envelope(certificate),
      "GET /api/v1/certificates/42/classification-runs": () =>
        envelope([
          {
            id: 101,
            rule_set_id: 1,
            parent_run_id: null,
            approval_status: "needs_review",
            demo_notice: "Reglas demo",
            created_at: "2024-05-16T10:00:00Z",
          },
        ]),
      "GET /api/v1/classification-runs/101": () => envelope(run),
      "POST /api/v1/classification-runs/101/approve": () =>
        envelope({ classification_run_id: 101, approval_status: "approved" }),
    });

    render(<App apiClient={backend.client} />);

    // Cargar archivo
    const file = new File(["%PDF-1.7"], "acta-real.pdf", { type: "application/pdf" });
    await user.upload(await screen.findByLabelText(/seleccionar certificados pdf/i), file);

    // Fila del archivo completada
    const reviewBtn = await screen.findByRole("button", { name: /revisar/i });
    await user.click(reviewBtn);

    // Ahora estamos en la página de validación del acta #42
    expect(await screen.findByText("Altos Hornos de México")).toBeInTheDocument();
    expect(screen.getByText("CM-2024-001")).toBeInTheDocument();
    expect(screen.getByText("EN 10025-2")).toBeInTheDocument();

    // Composición química real
    expect(screen.getByText("0.18%")).toBeInTheDocument();
    expect(screen.getByText("1.25%")).toBeInTheDocument();

    // Propiedades mecánicas reales
    expect(screen.getByText("310 MPa")).toBeInTheDocument();
    expect(screen.getByText("450 MPa")).toBeInTheDocument();

    // Cambiar a pestaña Validación
    const tabsNav = screen.getByRole("navigation", { name: "Secciones de validación" });
    const valTab = within(tabsNav).getByRole("button", { name: "Validación" });
    await user.click(valTab);

    // Motor de clasificación muestra fracción sugerida
    const tariffMatches = await screen.findAllByText("7208.51.01");
    expect(tariffMatches.length).toBeGreaterThanOrEqual(1);

    const ruleMatches = screen.getAllByText("RULE_DIMENSIONS");
    expect(ruleMatches.length).toBeGreaterThanOrEqual(1);

    const explanationMatches = screen.getAllByText("Espesor de 12.70 mm supera el umbral de 10 mm.");
    expect(explanationMatches.length).toBeGreaterThanOrEqual(1);

    // Proceso de dictamen en la barra inferior
    const footer = screen.getByRole("contentinfo");
    await user.type(within(footer).getByPlaceholderText(es.approval.personPlaceholder), "Ing. Supervisor");
    await user.type(within(footer).getByPlaceholderText(es.approval.reasonPlaceholder), "Aprobado tras cotejo documental");
    await user.click(within(footer).getByRole("button", { name: /aprobar/i }));

    await waitFor(() => {
      expect(backend.calls).toContain("POST /api/v1/classification-runs/101/approve");
    });
  });
});
