import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { App } from "@/app";
import { es } from "@/lib/i18n";
import { createFakeBackend, createFakeCertificate, createFakeClassificationRun, envelope, healthyRoutes, pdfFile } from "../support/fakeBackend";

async function openHistory(user: ReturnType<typeof userEvent.setup>) {
  await user.click(await screen.findByRole("button", { name: "Historial de actas" }));
}

describe("Carga, revisión e historial", () => {
  it("aplica filtros en el servidor y reinicia la paginación al limpiar", async () => {
    const backend = createFakeBackend({ ...healthyRoutes });
    render(<App apiClient={backend.client} />);
    const user = userEvent.setup();
    await openHistory(user);
    const form = screen.getByRole("form", { name: "Filtros de actas" });
    await user.type(within(form).getByLabelText("Colada"), "C-123");
    await user.type(within(form).getByLabelText("Serie del rollo"), "R/2");
    await user.selectOptions(within(form).getByLabelText("Estado de revisión"), "draft");
    await user.click(within(form).getByRole("button", { name: "Aplicar filtros" }));
    await waitFor(() => expect(backend.calls).toContain("GET /api/v1/certificates?heat_no=C-123&product_identifier=R%2F2&approval_status=draft"));
    await user.click(within(form).getByRole("button", { name: "Limpiar filtros" }));
    await waitFor(() => expect(backend.calls.filter((call) => call === "GET /api/v1/certificates")).toHaveLength(2));
  });

  it("guarda un borrador auditado y conserva las selecciones existentes", async () => {
    let run = createFakeClassificationRun();
    let body: unknown;
    const backend = createFakeBackend({ ...healthyRoutes,
      "GET /api/v1/certificates": () => envelope([createFakeCertificate()]),
      "GET /api/v1/certificates/42": () => envelope(createFakeCertificate()),
      "GET /api/v1/certificates/42/classification-runs": () => envelope([{ id: 101 }]),
      "GET /api/v1/classification-runs/101": () => envelope(run),
      "POST /api/v1/classification-runs/101/draft": (init) => {
        body = JSON.parse(String(init?.body));
        run = { ...run, approval_status: "draft" };
        return envelope({ classification_run_id: 101, approval_status: "draft" });
      },
    });
    render(<App apiClient={backend.client} />);
    const user = userEvent.setup();
    await openHistory(user);
    await user.click(await screen.findByRole("button", { name: "Abrir acta" }));
    await user.click(screen.getByRole("button", { name: "Dictamen de clasificación" }));
    const footer = await screen.findByRole("contentinfo");
    expect(within(footer).queryByRole("textbox")).not.toBeInTheDocument();
    await user.click(within(footer).getByRole("button", { name: "Guardar borrador" }));
    expect(await screen.findByText(/Borrador guardado/)).toBeInTheDocument();
    expect(body).toEqual({ person_name: "Administrador", reason: es.approval.defaultReason });
    expect(run.results[0]?.current_selection).not.toBeNull();
  });

  it("envía el candidato seleccionado con persona y motivo fijos sin pedir campos", async () => {
    const run = createFakeClassificationRun();
    let body: unknown;
    const backend = createFakeBackend({ ...healthyRoutes,
      "GET /api/v1/certificates": () => envelope([createFakeCertificate()]),
      "GET /api/v1/certificates/42": () => envelope(createFakeCertificate()),
      "GET /api/v1/certificates/42/classification-runs": () => envelope([{ id: 101 }]),
      "GET /api/v1/classification-runs/101": () => envelope(run),
      "POST /api/v1/classification-results/201/select": (init) => {
        body = JSON.parse(String(init?.body));
        return envelope({ candidate_id: 302 });
      },
    });
    render(<App apiClient={backend.client} />);
    const user = userEvent.setup();
    await openHistory(user);
    await user.click(await screen.findByRole("button", { name: "Abrir acta" }));
    await user.click(screen.getByRole("button", { name: "Validación" }));
    expect(screen.queryByLabelText("Nombre de quien valida")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Motivo del dictamen")).not.toBeInTheDocument();
    const candidates = await screen.findByRole("radiogroup", { name: "Candidatos disponibles" });
    await user.click(within(candidates).getAllByRole("radio")[1] as HTMLElement);
    expect(backend.calls.some((call) => call.startsWith("POST"))).toBe(false);
    await user.click(screen.getByRole("button", { name: "Elegir fracción" }));
    await waitFor(() => expect(body).toEqual({ candidate_id: 302,
      person_name: "Administrador", reason: "Selección de fracción y NICO sugeridos registrada por Administrador." }));
    expect(backend.calls.filter((call) => call === "GET /api/v1/classification-runs/101").length).toBeGreaterThan(1);
  });

  it("continúa consultando la carga al navegar al historial", async () => {
    let finish: (response: Response) => void = () => { throw new Error("La consulta aún no empezó"); };
    const backend = createFakeBackend({ ...healthyRoutes,
      "POST /api/v1/documents": () => envelope({ certificate_id: 42, document_id: 10, job_id: 7, duplicate: false }),
      "GET /api/v1/jobs/7": () => new Promise<Response>((resolve) => { finish = resolve; }),
    });
    render(<App apiClient={backend.client} />);
    const user = userEvent.setup();
    await user.upload(await screen.findByLabelText(/Seleccionar certificados PDF/), pdfFile());
    await waitFor(() => expect(backend.calls).toContain("GET /api/v1/jobs/7"));
    expect(screen.queryByRole("button", { name: "Ver procesamiento" })).not.toBeInTheDocument();
    await openHistory(user);
    expect(screen.getByText("1 documento(s) en procesamiento")).toBeInTheDocument();
    finish(envelope({ id: 7, document_id: 10, kind: "extract_document", status: "succeeded", progress: 100,
      attempts: 1, max_attempts: 3, error_code: null, error_message: null, result: null }));
    await waitFor(() => expect(screen.queryByText("1 documento(s) en procesamiento")).not.toBeInTheDocument());
    await user.click(screen.getByRole("button", { name: "Carga y revisión" }));
    expect(await screen.findByRole("button", { name: "Revisar" })).toBeInTheDocument();
  });
  it("genera clasificación para un acta existente y consulta el trabajo hasta terminar", async () => {
    let complete = false;
    let polls = 0;
    let body: unknown;
    const backend = createFakeBackend({ ...healthyRoutes,
      "GET /api/v1/certificates": () => envelope([createFakeCertificate()]),
      "GET /api/v1/certificates/42": () => envelope(createFakeCertificate()),
      "GET /api/v1/certificates/42/classification-runs": () => envelope(complete ? [{ id: 101 }] : []),
      "GET /api/v1/classification-runs/101": () => envelope(createFakeClassificationRun()),
      "POST /api/v1/certificates/42/reclassify": (init) => {
        body = JSON.parse(String(init?.body));
        return envelope({ certificate_id: 42, job_id: 12 }, 202);
      },
      "GET /api/v1/jobs/12": () => {
        polls += 1;
        if (polls === 1) return envelope({ id: 12, document_id: 10, kind: "reclassify", status: "running", progress: 40,
          attempts: 1, max_attempts: 3, error_code: null, error_message: null, result: {} });
        complete = true;
        return envelope({ id: 12, document_id: 10, kind: "reclassify", status: "succeeded", progress: 100,
          attempts: 1, max_attempts: 3, error_code: null, error_message: null, result: { classification_run_id: 101 } });
      },
    });
    render(<App apiClient={backend.client} />);
    const user = userEvent.setup();
    await openHistory(user);
    await user.click(await screen.findByRole("button", { name: "Abrir acta" }));
    const classification = await screen.findByRole("button", { name: "Generar clasificación" });
    expect(screen.queryByLabelText("Persona responsable")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Motivo del dictamen")).not.toBeInTheDocument();
    await user.click(classification);
    expect(await screen.findByText("Clasificando los rollos…")).toBeInTheDocument();
    expect(screen.getByRole("progressbar", { name: "Progreso de clasificación" })).toHaveAttribute("aria-valuenow", "40");
    expect(classification).toBeDisabled();
    await waitFor(() => expect(screen.queryByRole("progressbar", { name: "Progreso de clasificación" })).not.toBeInTheDocument(), { timeout: 4000 });
    expect(await screen.findByText("Clasificación terminada")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Generar clasificación" })).toBeEnabled();
    await user.click(screen.getByRole("button", { name: "Generar clasificación" }));
    await waitFor(() => expect(backend.calls.filter((call) => call === "POST /api/v1/certificates/42/reclassify")).toHaveLength(2));
    await user.click(screen.getByRole("button", { name: "Dictamen de clasificación" }));
    expect(await screen.findByRole("contentinfo")).toBeInTheDocument();
    expect(body).toEqual({ person_name: "Administrador", reason: es.workspace.classifyReason });
    expect(backend.calls).not.toContain("POST /api/v1/documents");
  });

  it("muestra el documento sin el bloque de descarte del historial", async () => {
    const backend = createFakeBackend({ ...healthyRoutes,
      "GET /api/v1/certificates": () => envelope([createFakeCertificate()]),
      "GET /api/v1/certificates/42": () => envelope(createFakeCertificate()),
      "GET /api/v1/certificates/42/classification-runs": () => envelope([{ id: 101 }]),
      "GET /api/v1/classification-runs/101": () => envelope(createFakeClassificationRun()),
    });
    render(<App apiClient={backend.client} />);
    const user = userEvent.setup();
    await openHistory(user);
    await user.click(await screen.findByRole("button", { name: "Abrir acta" }));
    expect(await screen.findByRole("heading", { name: "Información General" })).toBeInTheDocument();
    expect(screen.queryByText("Descartar del historial")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Motivo del descarte o restauración")).not.toBeInTheDocument();
    expect(backend.calls.some((call) => call.includes("/archive"))).toBe(false);
  });

});
