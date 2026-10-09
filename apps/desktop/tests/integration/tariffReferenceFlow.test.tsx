import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { App } from "@/app";

import {
  createFakeBackend,
  createFakeCertificate,
  createFakeClassificationRun,
  envelope,
  healthyRoutes,
  pdfFile,
  pdfResponse,
  type RouteHandler,
} from "../support/fakeBackend";

const SOURCE = "LIGIE capítulo 72 (fuente proporcionada)";
const NOTICE = "Fuente proporcionada con la marca SIN VIGENCIA; úsese sólo como referencia.";

function ligieResponse(
  entries: readonly { code: string; page: number | null; description: string }[],
  available = true,
): Response {
  return Response.json({
    data: entries.map((entry) => ({
      ...entry,
      kind: "nico",
      fraction: "7208.51.01",
      nico: "01",
      umt: "Kg",
      import_tax: null,
      export_tax: null,
    })),
    meta: {
      source: SOURCE,
      catalog_sha256: "c5fa",
      file_url: "/api/v1/rule-sources/ligie-72/file",
      file_status: available
        ? { available: true, code: null, message: null }
        : { available: false, code: "ligie_source_unavailable", message: "Configure HACKTITLAN_LIGIE_PDF_PATH." },
      notice: NOTICE,
    },
    error: null,
  });
}

/** El visor muestra el nombre de la fuente en su encabezado y en el iframe. */
function ligieFrame(): HTMLIFrameElement | undefined {
  return screen
    .queryAllByTitle(SOURCE)
    .find((element): element is HTMLIFrameElement => element instanceof HTMLIFrameElement);
}

async function openValidationTab(ligieRoute: RouteHandler) {
  const backend = createFakeBackend({
    ...healthyRoutes,
    "POST /api/v1/documents": () =>
      envelope({ document_id: 10, certificate_id: 42, job_id: null, duplicate: false }, 200),
    "GET /api/v1/certificates/42": () => envelope(createFakeCertificate({ id: 42 })),
    "GET /api/v1/certificates/42/classification-runs": () =>
      envelope([{ id: 101, rule_set_id: 1, parent_run_id: null, approval_status: "needs_review", demo_notice: "", created_at: "2024-05-16T10:00:00Z" }]),
    "GET /api/v1/classification-runs/101": () => envelope(createFakeClassificationRun()),
    // Candidato 7208.52 + NICO 01 del run de prueba.
    "GET /api/v1/rule-sources/ligie-72/entries/72085201": ligieRoute,
    "GET /api/v1/rule-sources/ligie-72/file": () => pdfResponse("ligie.pdf"),
  });
  const user = userEvent.setup();
  render(<App apiClient={backend.client} />);
  await user.upload(await screen.findByLabelText(/seleccionar certificados pdf/i), pdfFile("acta.pdf"));
  await user.click(await screen.findByRole("button", { name: /revisar/i }));
  const sections = screen.getByRole("navigation", { name: "Secciones de validación" });
  await user.click(within(sections).getByRole("button", { name: "Validación" }));
  await screen.findByRole("radiogroup", { name: "Candidatos disponibles" });
  return { user, backend };
}

describe("Referencia del NICO en la LIGIE", () => {
  it("al pulsar un NICO abre la LIGIE en su página, al lado de la clasificación", async () => {
    const { user, backend } = await openValidationTab(() =>
      ligieResponse([{ code: "7208.52.01-01", page: 24, description: "De espesor superior o igual a 4.75 mm" }]),
    );

    const candidates = screen.getByRole("radiogroup", { name: "Candidatos disponibles" });
    const radios = within(candidates).getAllByRole("radio");
    expect(radios[0]).toBeChecked();

    await user.click(within(candidates).getByRole("button", { name: /ver 7208\.52\.01 en la ligie/i }));

    // La pestaña LIGIE queda activa con su página y el PDF apunta a esa página.
    const ligieTab = await screen.findByRole("tab", { name: "LIGIE p. 24" });
    expect(ligieTab).toHaveAttribute("aria-selected", "true");
    // El PDF se descarga por el API y se muestra como archivo local en la página 24.
    await waitFor(() => expect(ligieFrame()?.getAttribute("src")).toMatch(/^blob:.*#page=24$/));
    expect(backend.calls).toContain("GET /api/v1/rule-sources/ligie-72/file");
    expect(screen.getByText(NOTICE)).toBeInTheDocument();

    // Consultar la referencia no cambia el candidato elegido.
    expect(radios[0]).toBeChecked();
    // La clasificación sigue visible al lado.
    expect(candidates).toBeVisible();

    await user.click(screen.getByRole("tab", { name: "Acta" }));
    expect(screen.getByRole("tab", { name: "Acta" })).toHaveAttribute("aria-selected", "true");
  });

  it("si la fuente repite el código, deja elegir la aparición en lugar de adivinar", async () => {
    const { user } = await openValidationTab(() =>
      ligieResponse([
        { code: "7208.52.01-01", page: 38, description: "Primera aparición" },
        { code: "7208.52.01-01", page: 39, description: "Segunda aparición" },
      ]),
    );

    await user.click(screen.getByRole("button", { name: /ver 7208\.52\.01 en la ligie/i }));
    expect(await screen.findByText(/aparece 2 veces en la fuente/i)).toBeInTheDocument();
    await waitFor(() => expect(ligieFrame()?.getAttribute("src")).toMatch(/#page=38$/));

    await user.click(screen.getByRole("button", { name: /página 39 · segunda aparición/i }));
    expect(ligieFrame()?.getAttribute("src")).toMatch(/#page=39$/);
    expect(screen.getByRole("tab", { name: "LIGIE p. 39" })).toBeInTheDocument();
  });

  it("si el servidor no tiene el PDF lo dice claramente", async () => {
    const { user } = await openValidationTab(() =>
      ligieResponse([{ code: "7208.52.01-01", page: 24, description: "Descripción" }], false),
    );

    await user.click(screen.getByRole("button", { name: /ver 7208\.52\.01 en la ligie/i }));
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("El PDF de la LIGIE no está disponible");
    expect(alert).toHaveTextContent("HACKTITLAN_LIGIE_PDF_PATH");
    expect(ligieFrame()).toBeUndefined();
  });
});

describe("Referencia LIGIE con un backend que aún no la publica", () => {
  it("explica que falta la ruta en el servidor en lugar de mostrar 'Not Found'", async () => {
    const { user } = await openValidationTab(() =>
      Response.json(
        { data: null, meta: {}, error: { code: "http_error", message: "Not Found", details: {} } },
        { status: 404 },
      ),
    );

    await user.click(screen.getByRole("button", { name: /ver 7208\.52\.01 en la ligie/i }));
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("El servidor todavía no ofrece la referencia LIGIE");
    expect(within(alert).getByRole("button", { name: "Reintentar" })).toBeInTheDocument();
  });
});
