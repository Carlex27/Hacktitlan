# Estado de implementación del backend

## En proceso

- Optimización conservadora de PDFs (9 de octubre de 2026): coincidencias de
  etiquetas reutilizadas sólo durante cada extracción, fuentes de verificación
  calculadas una vez por página y texto compacto calculado una vez por encabezado.
  Lectura digital libera las cachés de cada página y calcula SHA-256 por bloques.
  Comparación de nueve snapshots OCR: resultados completos idénticos, análisis
  de 1.43 a 0.53 s en una medición local; excluye inferencia OCR y Ollama y no
  constituye una medición del tiempo total de importación. Se conservan reglas,
  formatos, evidencia, parámetros OCR y verificaciones existentes.
  PDF digital de 50 páginas: layout y hash idénticos respecto al lector anterior.
  El test de integración `test_molino3_conflicting_ocr_proposal_can_be_accepted_with_audit`
  falla al buscar la lectura `39`, también ejecutando la extracción anterior;
  se conserva esa lógica y se registra la incidencia previa.

- Biblioteca de formatos, etapas 2 y 3 (9 de octubre de 2026): editor web con
  regiones, alternativa de teclado, columnas, guardado, pruebas y confirmación.
  Activación/retirada transaccionales, reconocimiento por encabezados estables,
  snapshots en jobs, procedencia y reprocesamiento explícito implementados.
  Migración 0011 validada sólo en hacktitlan_test; pendiente despliegue en la
  base de desarrollo cuya revisión Alembic no está registrada. Se mantiene
  revisión humana, el alcance de tablas simples y el modelo de confianza local.
  Ver [audit/FORMAT_LIBRARY_EDITOR.md](audit/FORMAT_LIBRARY_EDITOR.md).

- Biblioteca de formatos (9 de octubre de 2026): iniciada la etapa 0. Regiones
  relativas validadas y selección de evidencia con estados explícitos, sin
  modificar importación ni clasificación. Se inspeccionaron los seis PDFs
  aportados: todos son escaneados y necesitan OCR. Página 2 de COLD ROLL (B)
  procesada con caché OCR: 107 bloques y una tabla; superposición de cajas
  comprobada visualmente. Pendientes otros ejemplos, segmentación de paquetes,
  reconocimiento automático y editor web. Etapa 1: biblioteca de borradores,
  revisiones con control de concurrencia, preparación de layout y pruebas
  aisladas por jobs implementadas en API v1. La prueba fija configuración,
  revisión, layout y hash del extractor; no guarda productos ni modifica actas.
  Migración 0010 verificada en PostgreSQL de pruebas; aplicar al desplegar.
  Evidencia en [audit/FORMAT_LIBRARY_PILOT.md](audit/FORMAT_LIBRARY_PILOT.md).

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

- Alternativas por laminación desconocida (9 de octubre de 2026): sólo si
  frío y caliente resuelven cada uno una combinación fracción/NICO sin otras
  condiciones pendientes ni contradicciones. Se conservan `rolling=null`,
  estado `needs_review` y un factor explícito de confirmación del operador
  por candidato. Los códigos iguales se deduplican. Selección auditada probada
  mediante worker, PostgreSQL y API; no sustituye la laminación extraída.
  La regla general conserva ese límite. Por instrucción posterior del usuario,
  el zinc electrolítico admite sugerencias provisionales con química parcial,
  compatibles con ambos escenarios de laminación y sin contradicciones conocidas.
  Familia del acero y laminación permanecen pendientes y explícitas en los factores.
  Acta 15 de Molino 4: nueva clasificación 15, conservando la 14; comprobados
  en navegador los seis rollos con candidatos `72103002.01` y `72259101.00`.
  No se seleccionó candidato ni se modificaron valores extraídos.

- Diagnóstico del flujo activo de Molino 3 (9 de octubre de 2026): acta original
  6, documento 6, extracción 6 y trabajo 9; PDF SHA-256
  `7ebbf27942b5013b89b1f51decb2c220a80c09967a329827b95a2d3c828bfc9a`.
  El worker que atendió esa importación arrancó el 8 de octubre a las 19:37,
  antes de los cambios de OCR/refinamiento y metadatos. Se retiró manualmente
  y quedó el worker actualizado iniciado el 9 de octubre a las 01:35.
  La lectura real registró OCR antes/después del refinamiento: la lectura inicial
  mezcla columnas y pierde repeticiones; la refinada recupera los 11 rollos.
  Reprocesamiento por API: acta 9, revisión 2 de acta 6, documento 9,
  extracción 8, trabajo 12, worker `CarlonsioZ-28872a61`, clasificación 5.
  PostgreSQL y API conservan 12 elementos por rollo, C 0.35/0.33,
  1.8 × 895 mm, producto declarado, SAE 1035 y grado 1035.
  En navegador se abrieron los 11 detalles y los 11 selectores de candidatos:
  tres candidatos por rollo, todos pendientes de revisión. La extracción original
  permanece sin cambios. Evidencia local en `tmp/flow-audit/` (no versionada).
  Regresiones con PDF real: Molino 1, acta 10/trabajo 13, seis rollos con
  dimensiones y pesos iguales a la revisión anterior; Molino 2, acta 11/trabajo
  14, un rollo de 1.71 × 1220 mm y cinco elementos iguales a la referencia OCR.
  Ambos guardaron tres candidatos por rollo. Validación: 450 pruebas unitarias
  backend, 13 de integración, compileall, typecheck y lint correctos.
  Frontend: 176/177 pruebas correctas; fallo reproducible separado en
  `tariffReferenceFlow.test.tsx` al buscar el botón «Ver evidencia».
  No fue necesario agregar otra corrección al parser: el problema activo era
  que el worker anterior seguía procesando con código antiguo.

- Molino 3 (9 de octubre de 2026): refinamiento de celdas a 300 DPI con
  eliminación de bordes y detección visual de comillas de repetición. Se separa
  el nitrógeno químico de `N/mm²` y se reconoce la escala compartida de Cu/Ni/Cr.
  Comprobado contra el PDF: 11 rollos, coladas `3VL99` y `1FN43`, 12 elementos
  por rollo, C de 0.35/0.33, dimensiones 1.8 × 895 mm y norma SAE 1035.
  El grado 1035 se extrae de esa designación y se guarda en la colada.
  Regresión de extracción y flujo PostgreSQL/worker/API: tres candidatos por
  rollo, sujetos a revisión por factores no declarados. Los registros previos
  necesitan reprocesamiento con el worker actualizado.

- Eliminación definitiva de actas para pruebas (9 de octubre de 2026):
  `DELETE /api/v1/certificates/{certificate_id}`, sin persona ni motivo,
  habilitado sólo en `development`/`test`. Elimina datos dependientes y
  exportaciones afectadas; conserva otras actas y archivos compartidos.
  Rechaza trabajos en ejecución y restaura archivos ante fallo previo al commit.
  Migración `0009_certificate_deletion` para permisos de la cuenta del servicio.
  Validación: 20 pruebas de integración de eliminación, procesamiento y
  selección de candidatos aprobadas en PostgreSQL de pruebas; OpenAPI y
  compilación Python verificados. El entorno de pruebas no tiene el rol
  `hacktitlan_app`: la concesión de permisos a esa cuenta no se verificó allí.
  Operación y límites en `BACKEND_RUNBOOK.md`.

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
  - Libro Excel auditable de 8 hojas (`ExcelExportService`) generado íntegramente por el backend (`Resumen`, `Actas`, `Batches`, `Coladas`, `Composición`, `Clasificación`, `Evidencia`, `Auditoría`):
    - Hoja `Clasificación`: candidato elegido (`fraccion-nico`), alternativas 2 y 3, persona que seleccionó, motivo, fecha, factores clave y enlace interno clicable (`#'Evidencia'!A{row}`).
    - Hoja `Evidencia`: observaciones de extracción de cada producto mapeadas a sus códigos de regla/factor asociados desde `EvidenceLink`.
    - Hoja `Auditoría`: línea de tiempo consolidada de selecciones, aprobaciones y correcciones manuales con estado de vigencia explícito (`Vigente` vs `Reemplazada`).
    - Navegación interna entre hojas mediante fórmulas de hipervínculo nativas (`#'Hoja'!A1`) y saneamiento automático de datetimes sin zona horaria para compatibilidad total con openpyxl/Excel.
  - Compuerta estricta para reportes oficiales: `POST /api/v1/exports` y `ExcelExportService` exigen aprobación al 100% de todos los certificados y ejecuciones involucrados; si alguno está en `draft`, `needs_review` o `rejected`, la API rechaza con código HTTP 409 (`official_export_requires_approval`).
  - Título de hoja en A1 y aviso de consulta/demostración en A2; aprobación explícita por acta y fracción/NICO. Los reportes de consulta pueden incluir datos aprobados y pendientes.
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
  - El motor de clasificación se ejecuta aun con incidencias documentales o baja confianza OCR. Conserva sugerencias, factores y evidencia; los productos con incidencias bloqueantes quedan en `needs_review` con `quality_issues` para decisión humana.
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
  contra catálogo. La selección de sugerencias exige de una a tres opciones del motor, persona y
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
  cada trabajo para liberar recursos.
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
  base vacía con hashes coincidentes, y medición de consumo en el equipo disponible.
- Componente frontend para mostrar el PDF lateral, enfocar la página y dibujar
  el resaltado usando el contrato de evidencia ya disponible en el backend.
- Modelo generativo local opcional (Sección 14): integración inicial de Ollama
  implementada por solicitud del usuario; evaluación con modelos reales pendiente.

- Revisión web: endpoint de borrador auditado para ejecuciones pendientes o rechazadas, con conservación de selecciones y protección de ejecuciones aprobadas. Contrato generado en OpenAPI.

## Asistencia local de extracción (Ollama)

Integración opcional en el worker, desactivada por defecto y configurable con
`HACKTITLAN_OLLAMA_*`. Se valida JSON y evidencia literal; el backend normaliza
dimensiones y escalas químicas. Los resultados asistidos requieren revisión.
Los resultados existentes se conservan. Tanto adaptadores conocidos como la
extracción genérica verifican sus observaciones por campo con evidencia literal
y encabezados, sin reemplazarlas automáticamente. Migración 0008 guarda
`verification_json`; el detalle del certificado expone el contrato en OpenAPI.
Extraído muestra discrepancias y permite aceptar propuestas mediante la
corrección auditada existente. Los fallos del motor no eliminan la extracción.
Configuración y límites: `docs/BACKEND_RUNBOOK.md`, sección de Ollama.
Prueba real con `qwen3.5:4b`: detectó el ejemplo `13` bajo `C 10^-4`; el backend
calculó `0.0013 %` y conservó `0.13 %` hasta revisión. Pendiente medir exactitud y
rendimiento con certificados revisados; no se gestiona el proceso Ollama.
Propuestas normalizadas automáticas: química, ancho y espesor;
campos sin reglas o evidencia suficiente se señalan como no verificables.

Primera entrega del plan de formatos diversos: metadatos por etiquetas/posición
en todas las páginas y notas, fechas separadas y descripción del producto;
evidencia preservada y ambigüedad sin elegir un candidato arbitrario. Repetición
explícita limitada por tabla y composición por colada; filas identificadas vacías
no se descartan ni permiten rellenar posteriores por continuidad aparente.

Ollama verifica por rollo y consulta si el modelo admite visión. Para OCR con
PDF disponible envía recortes originales; una lectura visual distinta sólo queda
como propuesta con valor OCR, región y encabezado. Renderizado fallido vuelve a
texto y declara el fallo. No se añaden dependencias ni contratos API.
Prueba real de MOLINO 3: qwen3.5:4b recibió imágenes, pero no verificó el carbono
39/33. Se conserva 39/0.39 hasta revisión; no se considera solucionada esa lectura.
Validación: 437 pruebas unitarias/golden y 8 de integración de procesamiento.
Pendientes: recuperación parcial, reorientación OCR/PDF, precisión del corpus y
medición del uso de RAM/latencia. La configuración local sigue siendo opcional.

### Segunda entrega: recuperación parcial y corpus real

- Recuperación opcional de ancho, espesor y elementos químicos ausentes con
  Ollama, aun cuando ya existe un certificado. Se pide un rollo por consulta;
  referencias limitadas por JSON Schema, evidencia literal, unidad/escala y
  asociación de fila se comprueban antes de guardar una propuesta. No cambia
  valores originales ni crea una identidad nueva por similitud. Propuestas
  contradictorias entre páginas quedan no verificables.
- Una celda sin texto OCR puede verificarse visualmente si el rollo y el
  encabezado permiten delimitar su región. Un vacío no se rellena por proximidad.
  Los recortes respetan la orientación detectada por Paddle; tamaños incompatibles
  o errores de renderizado impiden validación visual y quedan registrados.
- Comparación de lecturas OCR superpuestas: MOLINO 3 conserva 39/0.39 y propone
  33/0.33 con celda y escala citadas. La API acepta la propuesta mediante la
  corrección auditada existente, conservando la observación anterior.
- Agrupación geométrica de lecturas idénticas de una misma celda. La nueva
  ejecución de MOLINO 4 mostró este duplicado; se reparó sin eliminar rollos
  distintos ni inventar identificadores. Se conservaron los seis rollos.
- Se admiten rollos al final de la página, filas identificadas vacías y metadatos
  con etiquetas encima del valor, incluyendo notas en páginas posteriores.
- Evaluación de PDF reales: 6/1/11/6 rollos y pesos 47,615/8,995/80,320/34,050 kg;
  ejecuciones OCR de 95.88/63.70/134.37/82.61 s en este equipo. MOLINO 4 se volvió
  a ejecutar tras reparar el duplicado. Estos datos corresponden al equipo de prueba.
- Prueba del LLM real: recuperación de ancho 1220 mm en una tabla de prueba
  formada con datos de MOLINO 2; original ausente conservado. Es una prueba
  controlada, no una medición de exactitud sobre todos los campos del PDF.

La aceptación de proveedores nuevos reutiliza el lector genérico y el fallback
local; no se agregan adaptadores por nombre. Aún pueden quedar fechas,
identificadores, símbolos o campos sin lectura comprobable. Se preservan para
revisión: la coincidencia del OCR o del LLM no autoriza una clasificación.
No se ha completado la revisión manual de todos los campos de los cuatro PDF,
ni la medición completa de consumo combinado OCR+LLM. El usuario retiró el
requisito de 8 GB de RAM; esa medición no condiciona la entrega a un límite fijo.

- Captura manual mediante el endpoint de selección documentado en OpenAPI: formato de 8/2 dígitos, justificación, candidato conditional con `details.manual=true`, conservación de sugerencias y cadena de reemplazos. Migración 0007 amplía el rango para registros manuales; el motor sigue limitado a tres sugerencias. No verifica automáticamente vigencia normativa. Cambios manuales bloqueados sobre ejecuciones aprobadas.

Por decisión del usuario, la selección auditada de fracción y NICO confirma la verificación humana de cada rollo. La aprobación del acta cierra la revisión completa; los datos faltantes y factores desconocidos del motor se preservan sin bloquear el cierre. Se mantienen bloqueos de contradicciones y cobertura incompleta.

### Química de tablas con un solo rollo (2026-10-09)

El refinamiento OCR genérico ahora relee las celdas químicas aunque exista un solo
rollo y no haya bloques fusionados. Limita el recorte de las escalas al encabezado
y elimina sus bordes antes de reconocer los superíndices. Se comprobó con los
bloques OCR y la imagen de MOLINO 2: C 0.08 %, Mn 0.34 %, P 0.015 %, S 0.008 %
y Al_total 0.029 %. La prueba conserva los bloques originales, incluida la lectura
incompleta de P como 5, junto a la lectura refinada 15. No se infieren escalas
ausentes ni se completan elementos con cero. Las extracciones guardadas requieren
reiniciar el worker y reprocesar el documento para incorporar el cambio.

### Formato Calvert incorporado (2026-10-09)

Por petición del usuario se añade el adaptador ArcelorMittal Calvert sobre el OCR existente. La carta complementaria conserva A1011 CS-B como evidencia y deja de crear un rollo ficticio A1011. Se validaron las cuatro páginas escaneadas, la extracción de un rollo con su colada, química en dos bandas y ensayos en otra página, y la persistencia mediante el worker/API en PostgreSQL de pruebas. La incorporación de este adaptador es una excepción solicitada al enfoque genérico descrito arriba; no modifica las reglas de clasificación. Los documentos previamente extraídos requieren reprocesamiento para actualizar sus datos.
### Calvert aluminizado con varios certificados (2026-10-09)

El adaptador admite varios certificados en un PDF y asocia química, dimensiones
y ensayos por página y número de certificado. Las descripciones `Aluminize Coil`
ya no dependen de `Hot Roll`; `Cold Roll Base` aporta la laminación declarada.
Se preserva la especificación de cada rollo y se recuperan los pesos de
recubrimiento por cara. La regresión usa el OCR real de las seis páginas de
`ALUMINIZE 1233 (B).pdf`: dos rollos y 17 elementos por rollo, dimensiones
1.2 × 1105 y 2 × 1073 mm, ensayos 407/602/28 y 417/594/27.
Los encabezados OCR `SI`, `AI` y `% Tolal` se reconocen conservando la evidencia.
El peso neto OCR `10,090,000` queda sin normalizar por separadores ambiguos;
el peso bruto legible de 10090 kg se presenta explícitamente como bruto.
Un archivo con varios números no recibe un número de acta único inventado;
los números originales se conservan en la evidencia de cada rollo.
Requiere reiniciar el worker y reprocesar para actualizar extracciones guardadas.

### Regresión de rasterización en Molino 1 (2026-10-09)

La selección de páginas para omitir portadas había reemplazado la rasterización
nativa de Paddle (escala 2, suavizado habilitado) por 150 dpi sin suavizado.
La reproducción con el PDF real produjo cinco rollos, tres lecturas de colada
(`2519114`, `7518114`, `2518114`) y sólo Si/Al soluble; el adaptador conocido
fallaba y el servicio recurría al extractor genérico. Se restauró la imagen de
entrada equivalente a la nativa: 144 dpi con `antialias=True`, comprobada píxel
a píxel contra PDFium. Se conserva la omisión de portadas Calvert.
La nueva ejecución real recuperó seis rollos, una colada `2518114` y los siete
elementos C, Si, Mn, P, S, Al soluble y Ti. Las pruebas ahora exigen todos esos
datos y comprueban la rasterización de páginas con y sin fallo del sondeo de
portadas. No se fusionan identificadores por semejanza ni se inventa química.
Validación operativa: worker reiniciado sin trabajos activos; reprocesamiento
por API del acta 27 creó la revisión 2 (acta 29), conservando la anterior.
El trabajo 36 terminó sin error en `needs_review`; la API publica seis rollos,
una colada y 42 mediciones químicas (siete por rollo), con los valores esperados.

## Filtros del historial


Corregida la búsqueda de actas por el título visible (número, ID o nombre de archivo),
espacios y comodines literales. Los filtros de colada, rollo y clasificación se
combinan sobre el mismo producto y la última ejecución. El intervalo por fecha
del acta excluye fechas desconocidas. Semántica documentada en OpenAPI y runbook;
pruebas sobre PostgreSQL cubren combinaciones, fechas y paginación.

Exportación por acta: UI con generación asíncrona y enlace de descarga. Se tipan las respuestas existentes en OpenAPI, se amplían proveedor/metadatos, dimensiones/pesos, códigos y aprobación; se corrige la vigencia de selecciones retiradas y se muestran rollos sin clasificación. Formato XLSX con filtros, fechas, precisión química y estados semánticos. Sin dependencias nuevas.

Compatibilidad de Excel: se elimina el AutoFilter adicional de hoja que se superponía al filtro de cada tabla y provocaba reparación al abrir. Pruebas del XML comprueban filtros exclusivos de tabla y rangos completos, también con hojas vacías.
