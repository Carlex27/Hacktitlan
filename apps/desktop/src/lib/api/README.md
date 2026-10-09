# Cliente del servicio central

Único punto de acceso del frontend al backend. Todo se importa desde
`@/lib/api`; las features nunca llaman a `fetch` directamente.

El detalle de actas reutiliza respuestas correctas durante cinco segundos, en
memoria y por instancia del cliente (máximo 50 entradas). `cacheTtlMs: 0` fuerza
una consulta nueva; la recarga explícita del detalle utiliza esta opción.
Cualquier POST, PATCH, DELETE o carga invalida la caché al comenzar y terminar,
incluso si falla; las lecturas previas a una escritura no repueblan la caché.
Los cambios de otros clientes pueden tardar hasta cinco segundos en verse al
consultar nuevamente. Listados, trabajos y exportaciones no usan esta caché.
Las importaciones sondean cada 1.5 segundos y, sin cambios de estado o progreso,
espacian las consultas a 3 y 6 segundos; un avance reinicia el intervalo.

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
| Fuente normativa | `PdfViewer` (vía `getBlob`) | `GET /rule-sources/{source_hash}/file`; la página viene en la evidencia `rule_source` (`reference.file_url`, `reference.page_number`) |
| Exportación | `createExport`, `getExport` | `POST /exports`, `GET /exports/{id}` |

Las rutas relativas que devuelve el backend (`file_url`, `detail_url`) se
convierten en URL absolutas con `api.url(ruta)`.

Al agregar un endpoint: DTO en `dto/<dominio>.ts`, función en
`endpoints/<dominio>.ts`, exportarlos en sus `index.ts` y probar ruta, método y
cuerpo en `tests/unit/lib/api/endpoints.test.ts`.

`uploadDocument` usa el cliente `ApiClient`. La variante anterior que recibe
una URL base se conserva como `uploadDocumentLegacy` para el importador anterior.
El módulo `documentReviews.ts` permanece porque esos adaptadores todavía importan
su función `request`; eliminarlo rompe la importación y el seguimiento de trabajos.
