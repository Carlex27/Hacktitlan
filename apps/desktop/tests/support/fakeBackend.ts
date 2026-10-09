import {
  createApiClient,
  type ApiClient,
  type CertificateDetailDto,
  type ClassificationRunDto,
  type EvidenceDetailDto,
  type FetchLike,
} from "@/lib/api";

export type RouteHandler = (init: RequestInit | undefined) => Response | Promise<Response>;

export function envelope(data: unknown, status = 200): Response {
  return Response.json({ data, meta: {}, error: null }, { status });
}

export function errorEnvelope(code: string, message: string, status: number): Response {
  return Response.json({ data: null, meta: {}, error: { code, message, details: {} } }, { status });
}

export function networkFailure(): never {
  throw new TypeError("Failed to fetch");
}

export interface FakeBackend {
  client: ApiClient;
  /** Rutas `"METHOD /path"` → manejador; se pueden reemplazar durante la prueba. */
  routes: Map<string, RouteHandler>;
  calls: string[];
}

export const TEST_BASE_URL = "http://backend.test";

export function createFakeBackend(routes: Record<string, RouteHandler> = {}): FakeBackend {
  const table = new Map(Object.entries(routes));
  const calls: string[] = [];
  const fetchImpl: FetchLike = async (input, init) => {
    const method = init?.method ?? "GET";
    const rawPath = input.replace(TEST_BASE_URL, "");
    const key = `${method} ${rawPath}`;
    calls.push(key);

    let handler = table.get(key);
    if (!handler) {
      const pathOnly = rawPath.split("?")[0] ?? "";
      handler = table.get(`${method} ${pathOnly}`);
    }
    if (!handler) {
      // Regex / prefix matching
      for (const [routePattern, routeHandler] of table.entries()) {
        const [routeMethod, pattern] = routePattern.split(" ");
        if (routeMethod === method && pattern && rawPath.startsWith(pattern)) {
          handler = routeHandler;
          break;
        }
      }
    }

    if (!handler) throw new Error(`Ruta no simulada: ${key}`);
    return handler(init);
  };
  return {
    client: createApiClient({ baseUrl: TEST_BASE_URL, fetch: fetchImpl, createRequestId: () => "req-1" }),
    routes: table,
    calls,
  };
}

/** PDF mínimo como lo envía el backend (con `attachment`, como en producción). */
export function pdfResponse(name = "acta.pdf"): Response {
  return new Response(new Blob(["%PDF-1.7"], { type: "application/pdf" }), {
    headers: {
      "Content-Type": "application/pdf",
      "Content-Disposition": `attachment; filename="${name}"`,
    },
  });
}

export const healthyRoutes: Record<string, RouteHandler> = {
  "GET /api/v1/health/live": () => envelope({ status: "ok" }),
  "GET /api/v1/health/ready": () =>
    envelope({ status: "ready", database: "available", storage: "available" }),
  "GET /api/v1/document-reviews": () => envelope([]),
  "GET /api/v1/certificates": () => envelope([]),
  // Documento 10: el que devuelven las cargas simuladas de las pruebas.
  "GET /api/v1/documents/10/file": () => pdfResponse(),
};

export function pdfFile(name = "molino-1.pdf"): File {
  return new File(["%PDF-1.7"], name, { type: "application/pdf" });
}

export function createFakeCertificate(
  overrides: Partial<CertificateDetailDto> = {},
): CertificateDetailDto {
  return {
    id: 42,
    document_id: 10,
    manufacturer: "Altos Hornos de México",
    certificate_no: "CM-2024-001",
    certificate_date: "2024-05-15",
    uploaded_at: "2024-05-16T10:00:00Z",
    revision_number: 1,
    previous_revision_id: null,
    approval_status: "draft",
    standard: "EN 10025-2",
    product_name: "Placa de acero laminada en caliente",
    demo_notice: "Certificado extraído para fines de demostración.",
    heats: [
      {
        id: 1,
        heat_no: "C-9876",
        standard: "EN 10025-2",
        grade: "S275JR",
      },
    ],
    products: [
      {
        id: 1,
        heat_id: 1,
        product_identifier: "PL-001",
        label_no: "ET-5544",
        product_type: "Placa",
        form: "Rectangular",
        coiled: false,
        rolling: "caliente",
        width_mm: "1524.00",
        thickness_mm: "12.70",
        weight_kg: "18500.50",
      },
    ],
    observations: [
      {
        id: 1,
        heat_id: 1,
        product_id: 1,
        field_path: "mechanical_properties.yield_strength",
        raw_value: 310,
        normalized_value: "310",
        unit: "MPa",
        confidence: 0.98,
        page_number: 1,
        bbox: [100, 200, 150, 220],
        source_text: "Límite elástico: 310 MPa",
        inherited: false,
        supersedes_id: null,
        is_current: true,
      },
      {
        id: 2,
        heat_id: 1,
        product_id: 1,
        field_path: "mechanical_properties.tensile_strength",
        raw_value: 450,
        normalized_value: "450",
        unit: "MPa",
        confidence: 0.99,
        page_number: 1,
        bbox: [100, 230, 150, 250],
        source_text: "Resistencia a la tracción: 450 MPa",
        inherited: false,
        supersedes_id: null,
        is_current: true,
      },
    ],
    chemical_compositions: [
      {
        id: 1,
        heat_id: 1,
        product_id: 1,
        element: "C",
        raw_value: 0.18,
        percentage: "0.18",
        inherited: false,
        source_label: "Carbono",
      },
      {
        id: 2,
        heat_id: 1,
        product_id: 1,
        element: "Mn",
        raw_value: 1.25,
        percentage: "1.25",
        inherited: false,
        source_label: "Manganeso",
      },
    ],
    ...overrides,
  };
}

export function createFakeClassificationRun(
  overrides: Partial<ClassificationRunDto> = {},
): ClassificationRunDto {
  return {
    id: 101,
    certificate_id: 42,
    rule_set_id: 1,
    parent_run_id: null,
    approval_status: "needs_review",
    input_snapshot: {},
    demo_notice: "Reglas LIGIE 2024 aplicadas.",
    results: [
      {
        id: 201,
        product_id: 1,
        product_type: "Placa laminada",
        fraction: "7208.51",
        nico: "01",
        description: "Productos laminados planos de hierro o acero sin alear, de anchura superior o igual a 600 mm",
        outcome: "classified",
        details: {},
        candidates: [
          {
            id: 301,
            rank: 1,
            fraction: "7208.51",
            nico: "01",
            description: "De espesor superior a 10 mm",
            support_level: "fully_supported",
            details: {},
            detail_url: "/api/v1/classification-candidates/301",
            factors: [],
          },
          {
            id: 302,
            rank: 2,
            fraction: "7208.52",
            nico: "01",
            description: "De espesor superior o igual a 4.75 mm pero inferior o igual a 10 mm",
            support_level: "conditional",
            details: {},
            detail_url: "/api/v1/classification-candidates/302",
            factors: [],
          },
        ],
        current_selection: {
          id: 401,
          candidate_id: 301,
          supersedes_selection_id: null,
          person_name: "María Pérez",
          reason: "Verificación de espesor 12.7mm acorde a partida 7208.51",
          workstation_name: "Estación 1",
          created_at: "2024-05-16T11:00:00Z",
        },
        selections: [
          {
            id: 401,
            candidate_id: 301,
            supersedes_selection_id: null,
            person_name: "María Pérez",
            reason: "Verificación de espesor 12.7mm acorde a partida 7208.51",
            workstation_name: "Estación 1",
            created_at: "2024-05-16T11:00:00Z",
          },
        ],
        steps: [
          {
            id: 501,
            sequence: 1,
            rule_code: "RULE_DIMENSIONS",
            outcome: "matched",
            inputs: { thickness: "12.70" },
            evidence: [],
            evidence_links: [
              {
                id: 601,
                source_type: "observation",
                field_path: "dimensions.thickness_mm",
                observation_id: 1,
                reference: {},
                detail_url: "/api/v1/evidence/601",
              },
            ],
            explanation: "Espesor de 12.70 mm supera el umbral de 10 mm.",
          },
        ],
      },
    ],
    ...overrides,
  };
}

export function createFakeEvidence(
  overrides: Partial<EvidenceDetailDto> = {},
): EvidenceDetailDto {
  return {
    id: 601,
    decision_step_id: 501,
    candidate_factor_id: null,
    source_type: "observation",
    field_path: "dimensions.thickness_mm",
    observation: {
      id: 1,
      raw_value: "12.70",
      normalized_value: "12.70",
      unit: "mm",
      confidence: 0.99,
      source_text: "Espesor: 12.70 mm",
    },
    document: {
      id: 10,
      file_url: "/api/v1/documents/10/file",
    },
    focus: {
      page_number: 1,
      bbox: [50, 100, 80, 120],
      can_focus_region: true,
      fallback: null,
    },
    ...overrides,
  } as EvidenceDetailDto;
}
