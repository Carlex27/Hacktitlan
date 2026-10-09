# Cliente del servicio central

Único punto de acceso del frontend al backend. Todo se importa desde
`@/lib/api`; las features nunca llaman a `fetch` directamente.

- `client.ts`: `createApiClient` (`get`, `post`, `postForm`, `getBlob`, `url`), encabezado
  `X-Request-ID` y cancelación con `AbortSignal`.
- `envelope.ts` / `errors.ts`: validación del sobre `{ data, meta, error }` y
  `ApiError` por tipo (`network`, `server`, `invalid_response`, `aborted`).
- `dto/`: tipos de transporte por dominio, idénticos a la respuesta del backend.
- `endpoints/`: una función por ruta del API v1, agrupadas por dominio.

| Dominio | Función | Ruta |
|---|---|---|
| Salud | `getHealthLive`, `getHealthReady` | `GET /health/live`, `GET /health/ready` |
| Documentos | `uploadDocument`, `getJob` | `POST /documents`, `GET /jobs/{id}` |
| Actas | `getCertificate` | `GET /certificates/{id}` |
| Calidad | `getCertificateQualityReport` | `GET /certificates/{id}/quality-report` |
| | `listDocumentReviews` | `GET /document-reviews` |
| | `reprocessCertificate` | `POST /certificates/{id}/reprocess` |
| OCR | `getOcrStatus`, `getOcrModels` | `GET /ocr/status`, `GET /ocr/models` |
| | `runOcrSmokeCheck` | `POST /ocr/smoke-check` |
| Clasificación | `listClassificationRuns` | `GET /certificates/{id}/classification-runs` |
| | `getClassificationRun` | `GET /classification-runs/{id}` (candidatos con factores, `current_selection`, evidencia) |
| | `getClassificationCandidate` | `GET /classification-candidates/{id}` |
| | `selectClassificationCandidate` | `POST /classification-results/{id}/select` |
| | `approveClassificationRun`, `rejectClassificationRun` | `POST /classification-runs/{id}/approve`, `/reject` |
| Evidencia | `getEvidence` | `GET /evidence/{id}` |
| Referencia LIGIE | `getLigieEntries` | `GET /rule-sources/ligie-72/entries/{code}` (página del NICO); PDF en `meta.file_url` |
| Exportación | `createExport`, `getExport` | `POST /exports`, `GET /exports/{id}` |

Las rutas relativas que devuelve el backend (`file_url`, `detail_url`) se
convierten en URL absolutas con `api.url(ruta)`.

Al agregar un endpoint: DTO en `dto/<dominio>.ts`, función en
`endpoints/<dominio>.ts`, exportarlos en sus `index.ts` y probar ruta, método y
cuerpo en `tests/unit/lib/api/endpoints.test.ts`.
