import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { StrictMode } from "react";
import { FormatLibrary } from "@/features/certificate-formats";
import { ApiClientProvider, type FormatVersionDto, type LayoutDto } from "@/lib/api";
import { createFakeBackend, envelope, errorEnvelope } from "../support/fakeBackend";

const config = { schema_version: 1 as const, fields: [], tables: [], recognition: [], form: null, rolling: null };
function setup() {
  let version: FormatVersionDto = { id: 2, format_id: 1, version_number: 1, revision: 1, status: "draft", configuration: config,
    configuration_sha256: "hash", person_name: "Test", reason: "Test", updated_at: "2026-10-09", lifecycle: [] };
  let tests: unknown[] = [];
  const layout: LayoutDto = { id: 3, document_id: 7, document_sha256: "pdf", document: { file_name: "example.pdf", sha256: "pdf", metadata: {},
    pages: [{ page_number: 1, width: 100, height: 100, rotation: 0, source: "digital", tables: [],
      blocks: [{ text: "ACTA-123", page_number: 1, confidence: 1, source: "digital", bbox: { x0: 10, top: 10, x1: 90, bottom: 20 } }] }] } };
  const backend = createFakeBackend({
    "GET /api/v1/certificate-formats": () => envelope([]), "GET /api/v1/certificates": () => envelope([]),
    "POST /api/v1/certificate-formats": init => {
      expect(JSON.parse(String(init?.body))).toMatchObject({ person_name: "Administrador", reason: "Configuración de formatos desde la biblioteca web" });
      return envelope({ id: 1, name: "Piloto", description: "" });
    },
    "GET /api/v1/certificate-formats/1": () => envelope({ id: 1, name: "Piloto", description: "", versions: [version] }),
    "GET /api/v1/certificate-format-versions/2/tests": () => envelope(tests),
    "PATCH /api/v1/certificate-format-versions/2": init => { const body = JSON.parse(String(init?.body)) as { configuration: FormatVersionDto["configuration"] };
      version = { ...version, revision: version.revision + 1, configuration: body.configuration }; return envelope(version); },
    "POST /api/v1/documents/7/layout-jobs": () => envelope({ job_id: 10 }),
    "GET /api/v1/jobs/10": () => envelope({ status: "succeeded", progress: 100 }),
    "GET /api/v1/documents/7/layout": () => envelope(layout),
    "GET /api/v1/document-layouts/3/pages/1/image": () => new Response(new Blob([], { type: "image/png" })),
    "POST /api/v1/certificate-format-versions/2/tests": () => { tests = [{ id: 5, version_id: 2, document_id: 7, layout_id: 3, current_revision: true, status: "succeeded",
      reviewed_by: null, result: { status: "success", certificate: { products: [{ product_id: "R1", thickness_mm: 0 }] }, evidence: [], diagnostics: [] } }]; return envelope({ ...(tests[0] as object), job_id: 10 }); },
    "POST /api/v1/certificate-format-tests/5/confirm": () => { const reviewed = { ...(tests[0] as object), reviewed_by: "Operador" }; tests = [reviewed]; return envelope(reviewed); },
    "POST /api/v1/certificate-format-versions/2/activate": () => { version = { ...version, status: "active" }; return envelope(version); },
  });
  vi.stubGlobal("URL", Object.assign(URL, { createObjectURL: vi.fn(() => "blob:test"), revokeObjectURL: vi.fn() }));
  render(<StrictMode><ApiClientProvider client={backend.client}><FormatLibrary documentId={7} certificateId={42} /></ApiClientProvider></StrictMode>);
  return { backend, user: userEvent.setup() };
}
async function create(user: ReturnType<typeof userEvent.setup>) {
  expect(screen.queryByLabelText("Persona que configura")).not.toBeInTheDocument();
  expect(screen.queryByLabelText("Motivo")).not.toBeInTheDocument();
  await user.type(screen.getByLabelText("Nombre del formato"), "Piloto");
  await user.click(screen.getByRole("button", { name: "Crear borrador" }));
  const toolbar = await screen.findByRole("banner", { name: "Acciones de la versión" });
  expect(within(toolbar).getByRole("button", { name: "Guardar borrador" })).toBeDisabled();
  expect(within(toolbar).getByRole("button", { name: "Guardar y probar" })).toBeDisabled();
  expect(screen.getByRole("button", { name: "Asignar campo a la zona" })).toHaveAccessibleDescription("Selecciona una zona del documento para asignar un campo o una tabla.");
  await user.click(screen.getByRole("button", { name: "Preparar páginas" }));
  await screen.findByText("Texto detectado");
  await user.click(screen.getByText("Texto detectado"));
  await user.click(screen.getByRole("button", { name: "Seleccionar bloque: ACTA-123" }));
  await user.click(screen.getByRole("button", { name: "Asignar campo a la zona" }));
  expect(document.querySelectorAll("select")).toHaveLength(0);
}
describe("Biblioteca de formatos", () => {
  it("configura una región con teclado, guarda, prueba, confirma y activa", async () => {
    const { user, backend } = setup();
    await create(user);
    await user.click(screen.getByRole("button", { name: "Guardar y probar" }));
    await screen.findByText("Extracción sin incidencias");
    await user.click(screen.getByRole("button", { name: "Confirmar valores contra el PDF" }));
    await screen.findByText("Prueba confirmada: Operador");
    await user.click(screen.getByRole("button", { name: "Activar versión" }));
    await screen.findByRole("button", { name: "Retirar del reconocimiento" });
    expect(backend.calls).toContain("PATCH /api/v1/certificate-format-versions/2");
  });
  it("conserva asignaciones al fallar el guardado y permite reintentar", async () => {
    const { user, backend } = setup();
    await create(user);
    const route = "PATCH /api/v1/certificate-format-versions/2";
    const original = backend.routes.get(route);
    if (!original) throw new Error("Fixture de guardado ausente");
    backend.routes.set(route, () => errorEnvelope("format_revision_conflict", "El borrador cambió", 409));
    await user.click(screen.getByRole("button", { name: "Guardar borrador" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("El borrador cambió");
    expect(screen.getByText("Número de acta · Página 1")).toBeInTheDocument();
    backend.routes.set(route, original);
    await user.click(screen.getByRole("button", { name: "Guardar borrador" }));
    await screen.findByText("Guardado");
  });
});
