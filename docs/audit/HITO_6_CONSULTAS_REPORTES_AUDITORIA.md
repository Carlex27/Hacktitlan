# Auditoría de Código — Hito 6: Consultas, Reportes y Auditoría Final

**Fecha de ejecución:** 8 de octubre de 2026  
**Rama:** `backend`  
**Objetivo del hito:** Implementar las capacidades de consulta avanzada, paginación estable por cursor, detalle histórico de selecciones con trazabilidad de reemplazos, generación del libro Excel auditable de 8 hojas y compuertas estrictas para reportes oficiales según la Sección 9 de `docs/BACKEND_COMPLETION_PLAN.md` ("Consultas, reportes y auditoría final").

---

## 1. Resumen Ejecutivo

En este hito se implementó la capa completa de consulta, auditoría y reportes del backend central:

1. **Consultas con filtros multidimensionales:** Soporte en `DocumentService.list_certificates` y en el endpoint `GET /api/v1/certificates` para filtrar por:
   - Presets temporales (`period`: `today`/`day`, `week`, `month`) y rango de fechas explícito (`date_from`, `date_to`).
   - Número de acta/certificado (`certificate_no`).
   - Fabricante (`manufacturer`).
   - Número de colada (`heat_no`).
   - Identificador de producto/rollo (`product_identifier`).
   - Fracción arancelaria (`fraction`) y NICO (`nico`).
   - Estados de aprobación documental (`approval_status`) y de procesamiento (`processing_status`).
2. **Paginación por cursor keyset `(sort_date, id)`:** Evita desplazamientos por inserciones. No representa una instantánea: las nuevas filas anteriores al cursor pueden aparecer en páginas posteriores; las posteriores al cursor quedan fuera de esa navegación.
3. **Detalle histórico de selecciones:** En `GET /api/v1/classification-runs/{run_id}` se exponen simultáneamente `current_selection` (la selección vigente actual) y `selections` (la línea de tiempo completa ordenada cronológicamente de selecciones históricas y reemplazos).
4. **Libro Excel auditable de 8 hojas (`ExcelExportService`):**
   - Hojas obligatorias generadas: `Resumen`, `Actas`, `Coladas`, `Rollos`, `Composición`, `Clasificación`, `Evidencia`, `Auditoría`.
   - Hipervínculos internos clicables de navegación nativa en Excel (`#'Hoja'!A1` y `#'Evidencia'!A{row}`).
   - Hoja `Clasificación`: Detalla candidato elegido, alternativas 2 y 3, persona que seleccionó, motivo, fecha de selección, resumen de factores clave y enlace directo a la evidencia del rollo.
   - Hoja `Evidencia`: Relaciona cada observación de producto con su código de regla/factor asociado de `EvidenceLink`.
   - Hoja `Auditoría`: Unifica cronológicamente los eventos de selección (`SELECCION_CANDIDATO`), aprobación (`APROBACION_ESTADO`) y corrección manual (`CORRECCION_DATO`) con indicación explícita de vigencia (`Vigente` vs `Reemplazada`).
5. **Compuerta estricta de reportes oficiales:**
   - Un reporte oficial (`official=True`) exige aprobación al 100% de todos los certificados y ejecuciones involucradas. Si alguno está en `draft`, `needs_review` o `rejected`, la API rechaza la solicitud inmediatamente con código HTTP 409 (`official_export_requires_approval`).
   - Un reporte no oficial (`official=False`) se marca visiblemente en la celda `A1` con la advertencia: `PRELIMINAR — PENDIENTE DE APROBACIÓN — DEMOSTRACIÓN — SIN VALIDEZ ADUANERA`.
6. **Auditoría de exportaciones:**
   - Registro en la base de datos de cada exportación con `filters_json`, `scope_json`, `person_name`, `workstation_name`, hash criptográfico `sha256` y `stored_file_id`.
   - Endpoint `GET /api/v1/exports/{export_id}` para consultar estado y metadatos de auditoría de la exportación.

---

## 2. Decisiones de Arquitectura y Diseño

### 2.1. Paginación Estable por Cursor Keyset vs Offset SQL
- **Problema:** La paginación tradicional basada en `LIMIT / OFFSET` sufre corrimiento de filas cuando nuevos documentos se ingieren concurrentemente entre la lectura de una página y la siguiente, provocando duplicados o filas saltadas.
- **Solución implementada:** Se implementó un cursor keyset codificado en base64 sobre la tupla `(sort_date, id)`.
- **Condición SQL:**
  $$\text{WHERE } (\text{sort\_date}, \text{id}) < (\text{cursor\_date}, \text{cursor\_id})$$
  ordenado de manera descendente: `ORDER BY sort_date DESC, id DESC`.
- **Verificación:** `test_cursor_pagination_stability_under_concurrent_insertions` prueba inserciones anteriores y posteriores al cursor. Conserva el orden de los registros originales y evita duplicados. Las actualizaciones de la fecha usada para ordenar no quedan cubiertas por esta garantía.

### 2.2. Resolución de Presets de Período Temporal (`resolve_period_dates`)
- La función pura `resolve_period_dates(period, today)` centraliza la lógica temporal:
  - `today` / `day`: fecha de hoy a hoy.
  - `week`: hoy menos 7 días a hoy.
  - `month`: hoy menos 30 días a hoy.
- Si se suministra un rango explícito (`date_from`, `date_to`), este tiene precedencia o complementa los presets sin sobreescribir arbitrariamente.

### 2.3. Exposición Dual: `current_selection` y Línea de Tiempo `selections`
- En auditoría aduanera no basta con conocer el estado final; es imperativo auditar si un analista seleccionó inicialmente una opción y un supervisor la corrigió posteriormente.
- El modelo `ClassificationSelection` mantiene `supersedes_selection_id`.
- La API en `GET /api/v1/classification-runs/{run_id}` resuelve la selección activa determinando la selección que no ha sido reemplazada por ninguna otra, colocándola en `current_selection`, y a la vez retorna el arreglo cronológico completo en `selections`.

### 2.4. Estructura y Estilo del Libro Excel Auditable (8 Hojas)
- Se utilizó `openpyxl` para generar un archivo Excel reproducible y estructurado con estilos visuales estandarizados:
  1. `Resumen`: Metadatos del lote exportado, conteos de actas, coladas, rollos, clasificaciones y selecciones, con hipervínculos a cada una de las otras 7 hojas (`#'Actas'!A1`, `#'Clasificación'!A1`, etc.).
  2. `Actas`: Identificador, documento, número, fabricante, fecha del certificado, fecha de carga, estado y revisión.
  3. `Coladas`: Identificador de colada, acta asociada, número de colada, norma, grado y propiedades metalúrgicas.
  4. `Rollos`: Dimensiones geométricas (ancho, espesor, peso), estado de enrollado, laminado y forma.
  5. `Composición`: Química desagregada por elemento (% C, Mn, Si, etc.) y etiqueta de origen.
  6. `Clasificación`: Registro por rollo del candidato elegido (`fraccion-nico`), alternativas de desempate 2 y 3, persona y motivo de la selección, resumen de factores técnicos y fórmula de hipervínculo interno directo a la hoja `Evidencia` (`#'Evidencia'!A{row}`).
  7. `Evidencia`: Observaciones de extracción física/química del documento con coordenadas de origen, texto fuente y código de regla asociado desde `EvidenceLink`.
  8. `Auditoría`: Timeline consolidado que une eventos de selección, aprobación y corrección manual, ordenados cronológicamente con indicación de vigencia (`Vigente` vs `Reemplazada`).

### 2.5. Compatibilidad de Datetimes en Excel y Sanitización
- Openpyxl no admite tipos `datetime` con información de zona horaria (`tzinfo`) en celdas de hojas de cálculo, generando una excepción si se escriben directamente.
- En `ExcelExportService._write_sheet` se implementó un saneamiento automático:
  ```python
  clean_row = [
      cell_val.astimezone(timezone.utc).replace(tzinfo=None)
      if isinstance(cell_val, datetime) and cell_val.tzinfo is not None
      else cell_val
      for cell_val in row
  ]
  ```
  Esto preserva el valor UTC exacto como fecha nativa de Excel sin depender de cadenas de texto desformateadas.

---

## 3. Modificaciones de Código

| Archivo | Tipo de Cambio | Justificación |
| :--- | :---: | :--- |
| `backend/app/application/document_service.py` | Modificado | Incorporación de filtros por `period`, `processing_status`, `heat_no`, `product_identifier`, `fraction`, `nico` y extracción de la función pura `resolve_period_dates`. |
| `backend/app/reporting/excel_export.py` | Reestructurado | Generación completa de las 8 hojas auditables, enlaces internos hipervinculados, tabla unificada de auditoría y saneamiento de fechas. |
| `backend/app/reporting/__init__.py` | Modificado | Exportación pública de `ExcelExportService`. |
| `backend/app/api/schemas.py` | Modificado | Adición de campos `filters` y `workstation_name` a `ExportRequest`. |
| `backend/app/api/app.py` | Modificado | Endpoint `GET /api/v1/exports/{export_id}`, validación 409 de compuerta oficial, parámetros de filtro y metadatos en `GET /api/v1/certificates`, y exposición de `current_selection` en `GET /api/v1/classification-runs/{run_id}`. |
| `backend/tests/unit/test_reporting_and_audit.py` | Creado | Suite exhaustiva de pruebas unitarias y de integración que verifica los 9 escenarios del hito. |

---

## 4. Cobertura de Pruebas y Verificación

Resultado histórico de la entrega original con `uv run pytest` (la revisión posterior figura en la sección 5):

```text
============================= test session starts =============================
platform win32 -- Python 3.12.14, pytest-9.1.1, pluggy-1.6.0
rootdir: C:\Users\ofici\OneDrive\Documents\GitHub\Hacktitlan
configfile: pyproject.toml
testpaths: backend/tests
plugins: anyio-4.15.1, cov-7.1.0
collected 177 items

backend\tests\golden\test_generic_extraction_corpus.py .....             [  2%]
backend\tests\golden\test_mill_certificates_corpus.py ....               [  5%]
backend\tests\integration\test_classification_candidate_selection.py ... [  6%]
backend\tests\integration\test_document_processing_flow.py ..            [  7%]
backend\tests\integration\test_document_quality_and_review.py ....       [ 10%]
backend\tests\integration\test_postgresql_contract.py ...                [ 11%]
backend\tests\unit\test_backend_foundations.py .......................   [ 24%]
backend\tests\unit\test_certificate_extraction_service.py ...            [ 26%]
backend\tests\unit\test_chapter72_coverage.py .......................... [ 41%]
..........                                                               [ 46%]
backend\tests\unit\test_chemistry_normalization.py .....                 [ 49%]
backend\tests\unit\test_classification_engine.py ....................    [ 61%]
backend\tests\unit\test_document_detection.py ....                       [ 63%]
backend\tests\unit\test_document_quality.py .........                    [ 68%]
backend\tests\unit\test_format_profiles.py ......                        [ 71%]
backend\tests\unit\test_generic_extractor.py ....                        [ 74%]
backend\tests\unit\test_mill_certificate.py ..........                   [ 79%]
backend\tests\unit\test_ocr_geometry.py ........                         [ 84%]
backend\tests\unit\test_ocr_models.py ........                           [ 88%]
backend\tests\unit\test_ocr_runtime.py .........                         [ 93%]
backend\tests\unit\test_pdf_reader.py ..                                 [ 94%]
backend\tests\unit\test_reporting_and_audit.py .........                 [100%]

======================= 177 passed, 1 warning in 8.29s ========================
```

### Casos de prueba específicos del Hito 6 (`test_reporting_and_audit.py`):
1. `test_resolve_period_dates_presets`: Valida la resolución exacta de `today`, `day`, `week`, `month`, `custom` y `all`.
2. `test_cursor_roundtrip_and_errors`: Valida la codificación/decodificación simétrica del cursor y el rechazo con `ApplicationError("invalid_cursor")`.
3. `test_export_request_validation`: Valida el rechazo de alcances vacíos y la aceptación de filtros y metadatos de auditoría.
4. `test_document_service_list_certificates_filters`: Verifica el filtrado efectivo por `certificate_no`, `heat_no`, `product_identifier`, `fraction`, `nico`, `period` y `approval_status`.
5. `test_cursor_pagination_stability_under_concurrent_insertions`: Demuestra que las páginas obtenidas mediante keyset cursor son disjuntas y estables ante inserciones concurrentes intermedias.
6. `test_classification_run_detail_exposes_current_selection_and_selections`: Comprueba que la selección activa se expone en `current_selection` y el historial completo ordenado en `selections`.
7. `test_excel_export_service_generates_eight_sheets_and_auditable_content`: Comprueba la creación de las 8 hojas, los hipervínculos nativos en Excel, los datos de alternativas en `Clasificación`, el enlace a `Evidencia` y el timeline en `Auditoría`.
8. `test_official_export_blocks_unapproved_records`: Comprueba que `official=True` bloquea actas no aprobadas arrojando excepción.
9. `test_api_certificates_and_export_endpoints`: Verifica los códigos HTTP (200, 202, 409) y los contratos OpenAPI para certificados y exportaciones.

---

## 5. Conclusión y Estado de Entrega

La revisión del 8 de octubre de 2026 encontró errores que las nueve pruebas originales no detectaban. Se corrigieron los siguientes hallazgos:

| Hallazgo | Corrección y regresión |
| :--- | :--- |
| El reporte oficial podía omitir actas sin clasificación o elegir una ejecución aprobada antigua cuando la última estaba pendiente. La API tampoco comprobaba las ejecuciones implícitas. | API y exportador comparten `resolve_runs`: requieren cobertura de cada acta y aprobación de cada ejecución elegida. Sin IDs explícitos se toma la última ejecución, sin retroceder a otra aprobada. Se prueban los tres casos de rechazo y HTTP 409. |
| Las ejecuciones implícitas podían cambiar entre la solicitud y el worker, sin reflejar el cambio en `scope_json`. | La solicitud guarda los IDs resueltos. El worker conserva también el alcance vacío explícito. Se prueba que una ejecución posterior no cambia los IDs elegidos. |
| Filtrar por coladas dejaba clasificaciones y correcciones de otros rollos dentro del libro. | Resultados y correcciones respetan el alcance de productos y observaciones. Se conserva evidencia general del acta. |
| El candidato elegido de rango 2 o 3 se repetía como alternativa y desaparecía el candidato de rango 1. | Las alternativas excluyen el candidato elegido y mantienen el orden de rango. |
| Una observación enlazada a varias reglas conservaba sólo la última. Un rollo sin evidencia apuntaba a la primera fila ajena. | Se conservan todos los códigos distintos. El enlace usa evidencia del rollo o evidencia general de su colada; sin evidencia se muestra el dato ausente sin enlace. |
| Aprobaciones antiguas y correcciones reemplazadas se marcaban como vigentes. | Sólo el último evento cronológico de aprobación queda vigente; la corrección usa `is_current` de su observación de reemplazo. |
| Texto externo que comienza con `=` se guardaba como fórmula de Excel. | Las cadenas se guardan como texto literal sin modificar su contenido. La prueba reabre el XLSX y comprueba tipo y valor. |
| Fracción y NICO podían coincidir en resultados distintos y devolver un falso positivo. | Ambos filtros se aplican al mismo resultado. |
| Cursores aceptaban booleanos, decimales, IDs fuera de rango y campos extra; los rangos de fechas invertidos fallaban silenciosamente. | Validación estricta de estructura y BIGINT positivo; rangos invertidos producen `invalid_date_range`. OpenAPI documenta HTTP 400. |
| IDs no positivos y estados de procesamiento desconocidos cruzaban la validación de entrada. | IDs positivos en `ExportRequest` y `ProcessingStatus` en consultas, declarados en OpenAPI. |

La suite dedicada contiene ahora **27 casos**, incluyendo las regresiones anteriores. La compilación estática de los módulos modificados y `git diff --check` pasan.

La primera ejecución general durante esta revisión registró **238 pruebas aprobadas y 8 fallidas** en `test_chapter72_coverage.py`. Se observaron cambios concurrentes en el motor de clasificación y sus pruebas, ajenos al Hito 6. La ejecución final sobre el estado compartido del repositorio terminó con **248 pruebas aprobadas y 2 advertencias** (deprecación de TestClient/httpx y ausencia de ccache para Paddle). No se verificó el diseño visual abriendo Microsoft Excel.
