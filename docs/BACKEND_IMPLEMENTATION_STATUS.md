# Estado de implementación del backend

## En proceso

- Progreso de importación conectado al trabajo real: avance por página durante
  OCR, guardado al 95 y finalización al 100 dentro de la transacción. Barra por
  archivo, consulta cada segundo, estados finales explícitos y recuperación de
  errores de conexión. Se prueban worker/API y hook de importación; validación
  visual pendiente del toolchain frontend.

- Hito 7: respaldo y restauración verificados; volumen de 18,250 actas y 273,750
  coladas medido en desarrollo. Consultas p95 entre 5.53 y 151.297 ms; XLSX de 300
  actas/4,500 rollos en 3.058 s; respaldo en 3.218 s y restauración en 19.479 s.
  Pendientes: objetivos acordados, servidor de demostración, OCR real y arranque
  tras omitir las 02:00. Evidencia en
  [`audit/HITO_7_RESPALDO_VOLUMEN_RENDIMIENTO.md`](audit/HITO_7_RESPALDO_VOLUMEN_RENDIMIENTO.md).

- Revisión de clasificación contra la fuente proporcionada (8 de octubre de
  2026): umbrales químicos y reglas NICO corregidas, PDF incluido con navegación
  normativa por página/región y bloqueo de factores desconocidos. Continúan
  pendientes vigencia oficial, calificadores industriales y visor frontend.
  Detalle en [`audit/CLASSIFICATION_SOURCE_REVIEW.md`](audit/CLASSIFICATION_SOURCE_REVIEW.md).

- Hito 3 permanece parcial: la extracción genérica falla de forma segura y
  conserva datos no mapeados, pero faltan los cuatro adaptadores específicos de
  formatos conocidos. El Hito 7 ya tiene implementación y mediciones de desarrollo.

## Implementado

- Importación XLSX (8 de octubre de 2026): almacenamiento original con hash,
  validación del paquete y límites, extracción sin OCR de tablas MOSSMEX y cartas
  por especificación, evidencia de hoja/celda y consulta documentada en OpenAPI.
  Verificada lectura de los tres libros proporcionados y flujo API/worker/PostgreSQL.
  Siempre requiere revisión; GENERAL conserva química ambigua sin normalizar,
  no se fusionan hojas ni se adoptan fracciones/NICO del archivo como resultados.
  Selector y envío React conectados a la API; visor Excel y validación visual
  pendientes del toolchain frontend.
  Detalles y límites en la sección Importación de Excel del runbook.

- Hito 6: Consultas, reportes y auditoría final implementado y verificado (auditoría en `docs/audit/HITO_6_CONSULTAS_REPORTES_AUDITORIA.md`).
  - Consultas avanzadas y filtros multidimensionales en `DocumentService.list_certificates` y `GET /api/v1/certificates`: presets de período (`today`/`day`, `week`, `month`) con helper puro `resolve_period_dates`, rango explícito (`date_from`, `date_to`), número de certificado, fabricante, colada (`heat_no`), producto (`product_identifier`), fracción arancelaria (`fraction`), NICO (`nico`), estado documental (`approval_status`) y estado de procesamiento (`processing_status`).
  - Paginación keyset `(sort_date, id)` sin desplazamiento por inserciones. No crea una instantánea ni garantiza estabilidad ante cambios de la fecha de ordenación; se prueban inserciones anteriores y posteriores al cursor.
  - Detalle histórico de ejecuciones en `GET /api/v1/classification-runs/{run_id}` exponiendo tanto `current_selection` (la selección activa vigente) como `selections` (la línea de tiempo cronológica completa de selecciones históricas y reemplazos).
  - Libro Excel auditable de 8 hojas (`ExcelExportService`) generado íntegramente por el backend (`Resumen`, `Actas`, `Coladas`, `Rollos`, `Composición`, `Clasificación`, `Evidencia`, `Auditoría`):
    - Hoja `Clasificación`: candidato elegido (`fraccion-nico`), alternativas 2 y 3, persona que seleccionó, motivo, fecha, factores clave y enlace interno clicable (`#'Evidencia'!A{row}`).
    - Hoja `Evidencia`: observaciones de extracción de cada producto mapeadas a sus códigos de regla/factor asociados desde `EvidenceLink`.
    - Hoja `Auditoría`: línea de tiempo consolidada de selecciones, aprobaciones y correcciones manuales con estado de vigencia explícito (`Vigente` vs `Reemplazada`).
    - Navegación interna entre hojas mediante fórmulas de hipervínculo nativas (`#'Hoja'!A1`) y saneamiento automático de datetimes sin zona horaria para compatibilidad total con openpyxl/Excel.
  - Compuerta estricta para reportes oficiales: `POST /api/v1/exports` y `ExcelExportService` exigen aprobación al 100% de todos los certificados y ejecuciones involucrados; si alguno está en `draft`, `needs_review` o `rejected`, la API rechaza con código HTTP 409 (`official_export_requires_approval`).
  - Marcado visual obligatorio de reportes preliminares en la celda A1 (`PRELIMINAR — PENDIENTE DE APROBACIÓN — DEMOSTRACIÓN — SIN VALIDEZ ADUANERA`).
  - Trazabilidad y auditoría completa de exportaciones en base de datos (`filters_json`, `scope_json`, `person_name`, `workstation_name`, hash criptográfico `sha256`, `stored_file_id`) y endpoint `GET /api/v1/exports/{export_id}`.
  - Suite dedicada ampliada a 27 casos. La revisión corrigió aprobación oficial incompleta, alcance por coladas, alternativas, evidencia, vigencia histórica, fórmulas externas y validación de filtros. La ejecución final sobre el repositorio compartido terminó con 248 pruebas aprobadas y 2 advertencias; ver auditoría para los límites de verificación.

- Hito 5: Cobertura completa de reglas aprobadas implementado y verificado (auditoría en `docs/audit/HITO_5_COBERTURA_REGLAS_AUDIT.md`).
  - Matriz de cobertura exhaustiva para las 29 partidas del Capítulo 72 y los 614 registros del catálogo oficial (`Chapter72CoverageMatrix`).
  - Clasificación de ramas formalizada en `BranchStatus`: 299 implementadas (`implemented`), 9 bloqueadas por hecho externo (`blocked_by_missing_fact`), 2 con anomalía oficial (`ambiguous_source`), y 304 fuera de alcance (`out_of_scope`). Cero ramas omitidas silenciosamente.
  - Cobertura determinista completa para las 9 partidas de laminados planos: `7208`, `7209`, `7210`, `7211`, `7212`, `7219`, `7220`, `7225` y `7226`.
  - Detección explícita de la anomalía oficial en la fracción `7219.35.02` (duplicada con contradicciones en páginas 38 y 39 del catálogo PDF `SIN VIGENCIA`); no se resuelve arbitrariamente por orden, sino que genera el paso `chapter72.stainless.source_anomaly_7219_35_02` con resultado `StepOutcome.AMBIGUOUS` y estado `needs_review`.
  - Incorporación en el modelo tipado `ProductFacts`, base de datos y snapshots de los hechos requeridos: `grain_oriented`, `magnetic_silicon`, `stainless_series`, `rolled_four_faces`, `clad` y `temper`.
  - Evaluación y filtrado riguroso de candidatos compatibles con registro justificado de descartes (`known_facts_conflict`, `outside_top_three`, `source_catalog_invalid`). Sin completar artificialmente a 3 opciones por similitud.
  - Inmutabilidad estricta de conjuntos de reglas aprobadas y retiradas (`validate_rule_set_immutability`, `RuleSetImmutabilityError`), auditoría de cambios antes de reclasificar (`compare_rule_sets`) y rechazo de ejecuciones con reglas retiradas (`rule_set_retired`).
  - Reproducibilidad matemática de reclasificaciones históricas mediante instantáneas.
  - Suite de 36 pruebas de frontera (`test_chapter72_coverage.py`) para umbrales exactos de aleación (Nota 1(f)), inoxidable (Nota 1(e)), dimensiones (600 mm, 0.35, 0.5, 1.0, 3.0, 4.75, 10.0 mm) y resistencia mecánica (355 MPa). Total de 168 pruebas pasando en suite completa.

- Hito 4: Calidad y revisión documental implementado y verificado.
  - Modelo de calidad y reporte de validación documental (`DocumentQualityReport`, `QualityIssue`, `validate_document_quality`).
  - Detección de familias de producto (`flat_rolled_coil`, `flat_rolled_plate`, `flat_rolled_general`) y validación de campos obligatorios.
  - Separación de categorías de incidencias (`missing`, `low_confidence`, `contradiction`, `anomaly`) con severidad `blocking` y `warning`.
  - Detección de contradicciones físicas (sumas químicas > 100 %, porcentajes fuera del rango 0-100 %, dimensiones <= 0, unidades incoherentes).
  - Detección de coladas duplicadas conflictivas y productos huérfanos.
  - Registro de procedencia (`digital_text`, `ocr_text`, `inherited`, `manual_capture`) y umbral mínimo de confianza (0.70).
  - Cola de revisión documental en `GET /api/v1/document-reviews` con filtros y resumen.
  - Reporte de calidad por acta en `GET /api/v1/certificates/{id}/quality-report`.
  - Reprocesamiento multi-etapa en `POST /api/v1/certificates/{id}/reprocess` (`extraction`, `normalization`, `classification`) preservando auditoría.
  - Bloqueo y compuerta en el motor de clasificación: productos con datos bloqueantes no reciben códigos adivinados y quedan en `needs_review` con `quality_issues`.
  - Sincronización de entidades en `ReviewService` con auditoría inmutable de correcciones.

- Runtime Python 3.12 y dependencias fijadas mediante `uv.lock`.
- Configuración tipada, errores estables, respuestas `data/meta/error`, logs
  JSON, correlación y timestamps con zona horaria.
- Esquema PostgreSQL de 22 tablas con `bigint identity`, integridad, índices y
  migración Alembic inicial; incluye el conjunto de reglas proporcionado en
  estado `draft` y con su hash de fuente.
- Almacenamiento central atómico y direccionado por SHA-256, deduplicación y
  revisiones de acta.
- API v1 de salud, carga/descarga, actas, coladas, rollos, evidencia, archivo,
  trabajos, cancelación, correcciones, aprobación/rechazo y exportación XLSX.
- Cola PostgreSQL con `SKIP LOCKED`, heartbeat, recuperación y tres intentos.
- Persistencia del contrato normalizado actual sin cambiar los cuatro parsers.
- Correcciones inmutables, eventos de aprobación y separación entre estado
  técnico y estado de aprobación.
- XLSX oficial/preliminar con ocho hojas, tablas, vínculos, formato, marca de
  demostración, validación y descarga administrada.
- Respaldo completo verificado, segunda copia, retención 7/4/12, ejecución a las
  02:00 con recuperación de tarea perdida y restauración sólo local.
- Scripts de arranque, preparación PostgreSQL y firewall Tailscale.
- Motor determinista conservador para laminados planos: familia metalúrgica,
  ramas iniciales 7208/7209/7210/7225, validación contra catálogo, candidatos,
  faltantes y pasos reproducibles.
- Reclasificación en segundo plano, ejecuciones enlazadas, instantáneas
  inmutables, captura manual de datos faltantes y bloqueo de aprobación cuando
  falta fracción o NICO.
- Generación y persistencia de hasta tres candidatos completos y validados
  contra catálogo. La selección exige exactamente tres opciones, persona y
  motivo; conserva historial inmutable y queda separada de la aprobación.
- Expansión de NICO para fracciones deterministas, con ranking estable y filtros
  de compatibilidad para 7208 y 7225. Incluye fronteras de boro, espesor,
  enrollado, decapado, resistencia, tubería y porcelanizado.
- API para consultar candidatos e historial mediante la ejecución y registrar
  la selección en `/api/v1/classification-results/{result_id}/select`.
- Enlaces `evidence_links` entre cada paso y sus observaciones exactas. La API
  `/api/v1/evidence/{evidence_link_id}` entrega página, coordenadas y URL
  administrada del PDF; sin coordenadas declara una vista de página completa.
- Persistencia de página, región, texto fuente y confianza cuando el extractor
  proporciona geometría para propiedades y composición química.
- Factores individuales e inmutables por candidato mediante
  `candidate_factors`: regla, operador, valor esperado, valor observado, unidad,
  resultado, explicación y evidencia específica.
- Detalle de candidato en
  `/api/v1/classification-candidates/{candidate_id}` y factores incluidos en el
  detalle de ejecución. Las opciones contradictorias no pueden seleccionarse.
- Registro de candidatos descartados por contradicción, catálogo inválido o
  posición fuera de las tres opciones mejor respaldadas.
- Flujo integral validado sobre PostgreSQL 18: carga `202`, almacenamiento,
  trabajo en cola, ejecución, persistencia de actas/coladas/productos/química,
  consulta por API y deduplicación por SHA-256.
- El worker sincroniza el estado técnico del documento al iniciar, reintentar o
  fallar. Los formatos incompletos terminan en `needs_review` y los PDF sin
  texto utilizable terminan en `needs_ocr` sin crear productos ficticios.
- Pruebas reales separadas en `hacktitlan_test` para conexión, versión,
  migraciones, disponibilidad de API y flujo completo de procesamiento.
- Integración opcional de PP-StructureV3 mediante `DocumentReader`, sin cargar
  PaddleOCR durante el arranque. Conserva texto, confianza, coordenadas y tablas.
- Diagnóstico de RAM, arquitectura, GPU NVIDIA, runtime Paddle y dispositivo
  activo mediante `/api/v1/ocr/status`. Selección `auto` prefiere `gpu:0` sólo
  cuando Paddle confirma CUDA; de lo contrario usa CPU.
- Si una inicialización o inferencia GPU falla, el lector reintenta una vez en
  CPU y registra el dispositivo efectivo. Los modelos se liberan al terminar
  cada trabajo para limitar memoria en equipos de 8 GB.
- Manifiesto tipado y administración del ciclo de vida de modelos mediante
  `OcrModelManager`: carpeta administrada fuera del repositorio, descarga
  atómica con `.part`, verificación previa de espacio en disco, comprobación de
  hashes SHA-256, reparación selectiva y eliminación segura.
- Normalización geométrica y sistema unificado de coordenadas por página en
  puntos (`pt`): transformaciones ante rotación (0°, 90°, 180°, 270°), escalado
  desde píxeles rasterizados y respaldo seguro a página completa sin fabricar
  coordenadas ficticias.
- Procesamiento secuencial por página en el worker con reporte de progreso
  (`job.progress`) y cancelación cooperativa segura (`OcrCancellationRequested`).
- Comprobación corta de runtime y consulta de modelos mediante
  `POST /api/v1/ocr/smoke-check` y `GET /api/v1/ocr/models`.
- Validación completa de los cuatro formatos reales de molino (`molino-1` a
  `molino-4`): escalado químico exacto (`13 × 10^-4 = 0.0013 %`), ditto marks,
  herencia de espesor y dimensiones, subtotales, recubrimientos y preservación
  de datos ausentes como `null` sin convertirlos en cero.
- Script operativo `scripts/install-ocr-runtime.ps1` con acciones `install`,
  `verify`, `repair`, `remove` y `status`. Sin el componente, se conserva
  exactamente el flujo `needs_ocr`.
- Extracción genérica determinista parcial de formatos desconocidos (Hito 3) mediante
  perfiles formales con umbral estricto (0.85), diccionario semántico multilingüe
  versionado (`v1.0.0`), extractor estructural de tablas con soporte multinivel y
  comillas de repetición (*ditto*), compilación de escalas químicas (`10^-2`, `10^-3`,
  `10^-4`, `%`), tolerancia a dimensiones ausentes sin forzar ceros, preservación de
  bloques y celdas no mapeados (`unmapped_blocks`) para auditoría y enrutamiento
  explícito a `needs_review` con `adapter="generic_layout_extractor"` sin inventar
  productos ficticios. Los perfiles conocidos sin adaptador registrado también
  terminan en `needs_review` y no usan el extractor genérico.

## Pendiente por diseño

El orden y los criterios de salida del trabajo restante están definidos en
[`BACKEND_COMPLETION_PLAN.md`](BACKEND_COMPLETION_PLAN.md).

- Hito 6: Consultas, reportes y auditoría final (Sección 9): filtros avanzados,
  cursores estables, XLSX oficial y preliminar con candidatos, factores y
  evidencia auditada, bloqueo de reportes oficiales sin aprobación completa.
- Hito 7: Respaldo, volumen y rendimiento (Sección 10): pruebas de siembra con
  18,250 actas y 273,750 coladas sobre 5 años, verificación de restauración en
  base vacía con hashes coincidentes, y presupuesto de memoria RAM $\le 8\text{ GB}$.
- Componente frontend para mostrar el PDF lateral, enfocar la página y dibujar
  el resaltado usando el contrato de evidencia ya disponible en el backend.
- Modelo generativo local opcional (Sección 14): únicamente evaluable tras el
  cierre del backend v1.
