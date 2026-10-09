# Plan de desarrollo del backend y PostgreSQL

## Resumen

La importación XLSX comparte almacenamiento, trabajos y revisión con PDF.
Se conserva hoja/celda como evidencia y las cartas de resistencia permanecen
como documentación de apoyo, sin vinculación automática por especificación.
La química ambigua exige confirmación antes de normalizar; filas entre hojas
no se deduplican por suposición. El envío React ya utiliza la API. El siguiente
trabajo frontend es habilitar su toolchain y presentar las celdas y advertencias
del endpoint documentado.

La revisión de reglas del 8 de octubre de 2026 está documentada en
[`audit/CLASSIFICATION_SOURCE_REVIEW.md`](audit/CLASSIFICATION_SOURCE_REVIEW.md).
Antes de declarar cobertura completa deben resolverse las brechas de vigencia,
definiciones de aceros especiales, calificadores NICO y captura auditada de los
hechos faltantes. La disponibilidad de una ruta ejecutable no certifica la
clasificación jurídica de todos sus NICO.

El backend será una API FastAPI central conectada a PostgreSQL 18. Administrará
los PDF originales, el procesamiento en segundo plano, el historial, las
correcciones, la aprobación, la clasificación, las exportaciones y los respaldos.
El frontend y el segundo equipo accederán exclusivamente por la API mediante
Tailscale.

El orden detallado desde el estado actual hasta el cierre del backend está en
[`BACKEND_COMPLETION_PLAN.md`](BACKEND_COMPLETION_PLAN.md). Ese documento
incluye la explicación individual por candidato, el cierre de OCR pendiente y
los criterios finales de aceptación.

La primera entrega implementable es API + PostgreSQL + almacenamiento + trabajos
+ historial. OCR, reportes y modelos locales se conectan posteriormente sin
reemplazar la normalización determinista existente.

## Tecnología y restricciones

- Python 3.12 administrado mediante `pyproject.toml` y `uv.lock`.
- FastAPI y Pydantic 2 con versiones fijadas.
- SQLAlchemy 2.1 síncrono, Alembic y psycopg 3.
- PostgreSQL 18 instalado como servicio nativo en Windows 11 x64.
  Se mantendrá actualizado dentro de su versión estable conforme a la
  [política de versiones soportadas](https://www.postgresql.org/support/versioning/).
- Sin Docker, nube, Redis, Celery ni cuentas de usuario en la primera versión.
- API limitada a la interfaz Tailscale en operación; sin modo offline.
- Sin presupuesto fijo de RAM; la selección de modelos depende de calidad y
  capacidad del equipo disponible. La aplicación base puede operar por CPU.

## Etapas

### 1. Fundamentos

- Configuración tipada para desarrollo, pruebas y servidor.
- Capas separadas de dominio, aplicación, repositorios, API e infraestructura.
- Errores estables, respuestas `data/meta/error`, logging estructurado,
  identificador de correlación y timestamps UTC.
- Conservación de `normalize_certificate` y todas sus pruebas actuales.

### 2. PostgreSQL y almacenamiento

- Migraciones para fabricantes, archivos, documentos, actas, coladas, productos,
  observaciones, composición, trabajos, extracciones, reglas, clasificaciones,
  decisiones, correcciones, aprobaciones, exportaciones y respaldos.
- Claves `bigint identity`, claves foráneas indexadas, restricciones de dominio e
  índices compuestos orientados a las consultas históricas.
- PDF en almacenamiento central configurable, publicados atómicamente después
  de calcular SHA-256.
- La ruta predeterminada es `C:\ProgramData\Hacktitlan\storage`; la escritura
  usa un temporal, verifica nuevamente el hash y publica mediante renombrado
  atómico.
- Mismo hash: operación idempotente. Mismo número de acta y distinto hash:
  revisión vinculada.
- Sin eliminación física; sólo archivado.

### 3. API y trabajos

- Salud, disponibilidad, carga/descarga, consultas paginadas, detalle histórico,
  evidencia, trabajos, correcciones, reclasificación, aprobación y rechazo.
- Carga `202 Accepted` con `document_id` y `job_id`.
- Cola PostgreSQL con `FOR UPDATE SKIP LOCKED`, heartbeat, recuperación de
  trabajos abandonados y máximo tres intentos.
- Estados técnicos independientes de `draft`, `needs_review`, `approved` y
  `rejected`.
- Persona y motivo obligatorios para corregir, aprobar o rechazar; equipo y fecha
  agregados por el backend.

### 4. Persistencia e historial

- Persistir actas, coladas, productos, composición y evidencia desde el contrato
  normalizado actual.
- Una corrección crea una nueva observación enlazada; nunca sobrescribe la
  anterior.
- Cada clasificación conserva entrada, reglas y pasos de decisión inmutables.
- Consultas mediante cursor por fecha, acta, fabricante, colada, producto,
  fracción, NICO y estado.
- Los periodos usan fecha del acta por defecto y admiten fecha de carga.

### 5. Clasificación, reportes y respaldo

La ejecución del Hito 7 está registrada en
[`audit/HITO_7_RESPALDO_VOLUMEN_RENDIMIENTO.md`](audit/HITO_7_RESPALDO_VOLUMEN_RENDIMIENTO.md).
El respaldo usa un snapshot PostgreSQL compartido entre conteos y `pg_dump`,
valida el ZIP antes de publicarlo y conserva un primario verificable si falla
la segunda copia. La restauración local exige base y carpetas vacías. El volumen
de cinco años ya se midió en desarrollo; la aceptación del servidor sigue pendiente.

- Reglas versionadas exclusivamente desde el PDF proporcionado.
- Resultados y reportes con la marca
  `DEMOSTRACIÓN — SIN VALIDEZ ADUANERA`.
- Reportes oficiales sólo con resultados aprobados; los demás son preliminares.
- XLSX por acta, colada o periodo conforme a `EXCEL_EXPORT_REQUIREMENTS.md`.
- Respaldo diario a las 02:00: 7 diarios, 4 semanales y 12 mensuales, con
  `pg_dump`, archivos, reglas, manifiesto y segunda copia configurable.
- Si Windows estaba apagado a las 02:00, el respaldo se ejecuta al iniciar.
- La exportación manual integral verifica hashes y `pg_restore --list`.
- Restauración sólo desde el servidor, nunca por endpoint remoto.

### 6. OCR y modelos posteriores

- PaddleOCR/PP-Structure implementarán la interfaz `DocumentReader`.
- Sin paquete OCR, el PDF se conserva y el trabajo termina en `needs_ocr`.
- Los modelos opcionales respetan `LOCAL_MODELS_REQUIREMENTS.md`.
- Se detectará CPU/GPU y se descargará únicamente el runtime compatible.
- Ningún modelo sustituye las reglas de normalización, validación o
  clasificación.

## Contratos públicos

- Respuestas uniformes `data`, `meta`, `error`.
- Cursores opacos basados en fecha e identificador.
- Desconocido se representa como `null`, nunca como cero o falso.
- Límite inicial configurable de 100 MB por PDF.
- Descargas por identificador administrado; no se aceptan rutas del cliente.
- La clasificación pertenece al producto, aunque la vista se agrupe por colada.

## Pruebas y aceptación

- Conservar las 24 pruebas existentes.
- Probar estados, restricciones, deduplicación, revisiones, cursores,
  aprobaciones, correcciones, worker y almacenamiento atómico.
- Integración real contra `hacktitlan_test`, incluyendo migraciones.
- Probar interrupción/reanudación de trabajos, correcciones inmutables y
  reproducción exacta de ejecuciones históricas.
- Restauración completa en una base vacía.
- Prueba de volumen de cinco años: 18,250 actas y hasta 273,750 coladas.
- Verificar paginación y filtros sobre ese volumen, que sólo resultados
  aprobados entren en reportes oficiales y que toda salida conserve la marca de
  demostración.
- Verificación en Windows 11 x64 con el hardware disponible, sin límite fijo de RAM.

## Supuestos cerrados

- Primer hito: API + PostgreSQL + almacenamiento + trabajos + historial.
- PostgreSQL será un servicio nativo, no Docker.
- Sin cuentas de usuario; Tailscale es la única barrera de acceso de esta etapa.
- Persona y motivo son obligatorios para aprobar, rechazar o corregir.
- Sin servidor no habrá consulta ni trabajo offline.
- Reportes agrupados por fecha del acta.
- Respaldo 7 diarios, 4 semanales y 12 mensuales con segunda copia configurable.
- Este archivo fue creado antes del primer cambio de implementación y conserva
  el plan aprobado completo.


## Plan de extracción y verificación con evidencia — 8 de octubre de 2026

Implementación iniciada: primera entrega estructural y verificación visual opcional.
Alcance: recuperar información
presente en el documento y detectar lecturas incorrectas sin inventar valores.
No garantizar extracción completa cuando el documento omite un dato o es ilegible.
Reutilizar OCR, normalización, observaciones, correcciones y trabajos actuales.
No cambiar reglas de clasificación ni aprobación como parte de esta mejora.

Avance de esta entrega:
- Metadatos generales en todas las páginas, etiquetas y notas, con evidencia;
  emisión, embarque y entrega separados; valores contradictorios quedan ausentes.
- Símbolos explícitos de repetición adicionales; filas identificadas se conservan
  aunque estén vacías; no se hereda química entre coladas ni datos entre tablas.
- Fecha de emisión en inglés normalizada y eliminación del fallback de entrega.
- Consultas de verificación por rollo; modelos con visión reciben un recorte del
  PDF original con fila y encabezados. La respuesta sólo crea una propuesta.
- Pruebas unitarias/golden: 437 pasan. Integración de procesamiento y persistencia:
  8 pasan, incluyendo MOLINO 3 desde una captura OCR y separación de fechas.
- Prueba visual real de carbono de MOLINO 3 con qwen3.5:4b: admite imágenes,
  pero devuelve not_verifiable; todavía no se cumple la salida 39/33 de fase 4.
  No se corrigió el certificado guardado ni se declaró exactitud completa.

Pendiente: corpus completamente revisado, recuperación parcial selectiva de
metadatos/identidades/celdas sin evidencia, reconciliación de lecturas OCR,
alineación de páginas reorientadas, evaluación visual y presupuesto de memoria.
Aceptar proveedores nuevos no implica poder completar datos omitidos o ilegibles.

Segunda entrega implementada: recuperación parcial de dimensiones/química como
propuestas citadas, regiones visuales para celdas sin texto OCR, comparación de
lecturas OCR contradictorias y agrupación de cajas superpuestas de una misma
identidad. El caso 39/33 ahora tiene propuesta 0.33 revisable por la API, aunque
el LLM visual por sí solo no había resuelto la celda. Se ejecutaron los cuatro
PDF reales y se recuperaron 6/1/11/6 rollos; MOLINO 4 reveló un duplicado que se
reparó y volvió a probar. No se garantiza la exactitud de todos los campos.
El evaluador reproducible es scripts/evaluate_certificate_extraction.py.
Metadatos/identidades ambiguas y la evaluación completa por campo siguen
requiriendo el corpus revisado y la revisión humana descritos en estas fases.

### Diagnóstico confirmado

- MOLINO 3 contiene una tabla rasterizada: no entrega texto con pdfplumber.
- La extracción actual conserva 11 rollos, pero pierde dimensiones después de
  la primera fila y lee el carbono de 1FN43 como 39 donde la revisión visual
  y el JSON anterior indican 33. La escala del encabezado debe verificarse.
- Se debe confirmar visualmente el identificador de la otra colada: 3VL99/BVL99.
  No convertir una lectura ambigua en una identidad definitiva.
- El extractor genérico contempla comillas de repetición; hay que reparar su
  comportamiento ante símbolos perdidos, celdas vacías y pérdida de continuidad.
- El LLM actual recibe texto y tablas del OCR, no píxeles. Cuando ya existe un
  certificado, sólo verifica; no ejecuta la extracción alternativa.
- En el diagnóstico inicial, la configuración del proyecto tenía Ollama deshabilitado. La
  configuración efectiva del worker aún debe comprobarse; no confundirla con
  la del proceso API ni con que el modelo esté instalado. Esta entrega activa
  HACKTITLAN_OLLAMA_ENABLED en el .env local; el worker en ejecución requiere reinicio.
- La persistencia admite delivery_date_raw como alternativa para certificate_date.
  Fecha de emisión y fecha de embarque deben mantenerse separadas.
- Los fixtures/JSON anteriores ayudan, pero no prueban la calidad del OCR real.
  No sustituir el PDF por un fixture para declarar éxito de extracción.

### 1. Referencia verificada y medición inicial

Revisar visualmente MOLINO 1–4, empezando por MOLINO 3. Completar el corpus
existente con valores esperados, página/región, campo, rollo/colada y escalas.
El JSON anterior es un borrador de referencia; confirmar cada campo crítico
contra el PDF. Guardar resultados del pipeline real y compararlos con esa
referencia, incluyendo omisiones, errores y asociaciones incorrectas.

Salida: inventario revisado de datos disponibles y medición inicial por campo.
Para MOLINO 3: 11 rollos; dos coladas con identidad comprobada; 1.800 mm y
895 mm en las filas sustentadas por repetición; carbono de 1FN43 de 0.33 %
si se confirma 33 con escala 10^-2; totales declarados de 11 y 80,320 kg.
Verificar emisión JUN. 12, 2026 separadamente del embarque aproximado
ON/ABOUT JUN. 28, 2026. No normalizar una fecha aproximada como exacta.

### 2. Reparar lectura estructural y normalización determinista

Trabajar en generic_extractor, layout_rows, vocabulary, mill_certificate y
persistence según los fallos reproducidos. Mantener filas, columnas, encabezados,
unidades y contexto de página; refinar sólo las regiones problemáticas.

- Resolver repetición únicamente ante símbolo explícito comprobado, en la misma
  columna y con un origen válido. No rellenar vacíos por proximidad.
- Mantener cadenas de origen para herencia; no trasladar química entre coladas
  sin evidencia, aunque las dimensiones puedan repetirse entre ellas.
- Buscar fabricante, fechas y descripción en encabezados, notas y pie, mediante
  etiquetas y relaciones espaciales; distinguir cliente de fabricante.
- Conservar HOT ROLLED SHEET-COIL (MILL EDGE) como descripción original y
  normalizar sólo los atributos sustentados por ese texto.
- Separar emisión, embarque y entrega. Retirar el fallback que presenta entrega
  como fecha del acta; revisar compatibilidad y registros anteriores antes de
  cualquier corrección, sin migración masiva silenciosa.
- Mantener Decimal, escalas originales y null para ausencias. No elegir un valor
  por parecer más plausible para el grado del acero.

Salida: pruebas sintéticas y del corpus pasan; cada valor heredado conserva
el símbolo y su origen. Los documentos ya correctos no sufren regresiones.

### 3. Asistencia LLM selectiva para extracción parcial

Comprobar configuración efectiva del worker, disponibilidad y modelo local.
Registrar si hubo asistencia, modelo, versión de instrucciones, duración y
motivo de activación; usar metadata y logs actuales antes de crear endpoints.

Activar recuperación para campos faltantes, símbolos/identidades ambiguos,
encabezados sin escala, contradicciones y regiones no mapeadas, aun si el parser
ya produjo un certificado. Dividir por región/rollo para no exceder el contexto;
no truncar silenciosamente ni enviar siempre la página completa.

La salida debe citar campo, valor literal, identidad y fuente/encabezado. El
backend comprueba referencias, asociación y unidades antes de normalizar.
Reutilizar schemas y verificaciones existentes. Una respuesta inválida, timeout
u Ollama no disponible conserva el resultado inicial y declara needs_review.

Salida: un certificado parcial recibe propuestas verificables sin duplicar
rollos, reemplazar datos buenos ni perder cancelación y progreso del trabajo.

### 4. Segunda lectura visual de campos críticos

Verificar primero si el modelo instalado admite imágenes y si su ejecución
cabe en el equipo disponible; no cambiar modelos ni instalar dependencias
sin justificarlo. Si no es viable, mantener segunda lectura OCR y revisión humana.

Enviar recortes que incluyan celda, encabezado/escala e identidad del rollo o
colada. Mantener transformación de coordenadas al PDF original. Para metadatos,
incluir su etiqueta y contexto. No usar recortes de números aislados.

Comparar lectura OCR y visual en química, dimensiones, identificadores y fechas.
La coincidencia sobre el mismo texto OCR no cuenta como verificación visual.
El LLM no decide por votación ni por su propia confianza. Lecturas distintas,
como 39/33, generan propuesta de corrección y revisión; no sobrescriben valores.

Salida: el caso 39/33 queda detectado con evidencia y el valor correcto puede
aceptarse mediante una corrección auditada. Nunca aplicar una cifra contradictoria
sólo porque el modelo la afirmó. Medir latencia/memoria antes de fijar límites.

### 5. Integración con revisión humana y API

Reutilizar observaciones, verification_json, correcciones y visor actuales.
Presentar extraído, propuesta, valor normalizado y evidencia del campo; explicar
faltante, discrepancia, fallo técnico y pendiente de revisión por separado.
Si hacen falta datos de emisión/embarque o procedencia que el contrato actual
no representa, revisar app.py, schemas.py y OpenAPI generado antes de extenderlo;
actualizar DTO, persistencia, migración y pruebas en el mismo cambio.

Revisar PRODUCT.md, DESIGN.md y FINESSE_DESIGN_REFERENCE.md antes de implementar
los cambios visuales. Mantener componentes y textos centralizados. Aprobar un
rollo/acta registra la revisión humana según el flujo acordado; no convierte
un campo desconocido en un dato verificado ni borra discrepancias o evidencia.
Una corrección posterior que afecte clasificación exige una nueva ejecución;
no modificar el snapshot de una ejecución cerrada.

Salida: aceptación/rechazo de propuestas funciona, conserva historial y permite
regenerar clasificación. Validar loading, empty, success, needs_review, error,
teclado y pantallas relevantes en navegador.

### 6. Pruebas y puesta en uso

Ampliar tests existentes de generic_extractor, mill_certificate, OCR real,
ollama_extraction, ollama_verification, calidad, persistencia y procesamiento.

- Casos: 33/39, 3/B, comillas encadenadas y sin origen, cambio de colada, celdas
  vacías, encabezados multinivel, química repetida y escalas 10^-2/10^-3/10^-4.
- Metadatos en notas, fabricante frente a cliente, emisión frente a embarque,
  fechas aproximadas, varias páginas y filas reordenadas.
- Respuestas LLM malformadas, citas inexistentes, asociación equivocada,
  duplicados, texto documental con instrucciones, límites, timeout y cancelación.
- Flujo real: importar PDF → detectar discrepancia → aceptar corrección →
  reclasificar → confirmar rollos → cerrar acta. No dar por probado este flujo
  usando sólo fixtures o mocks del modelo.

Criterios de entrega: en el corpus revisado, todos los campos críticos tienen
valor correcto con evidencia o quedan explícitamente pendientes; ningún valor
erróneo del corpus se acepta silenciosamente, ni se inventan campos ausentes.
MOLINO 3 conserva sus 11 rollos y asociaciones, dimensiones comprobables,
química/escalas verificadas y metadatos separados. Los cuatro PDFs pasan sus
comparaciones; registrar resultados y límites fuera del corpus, sin prometer
precisión universal ni presentar quality_score como probabilidad de acierto.

Reprocesar primero una copia de prueba de MOLINO 3, comparar revisiones y medir
llamadas al LLM, latencia y memoria. Reprocesar datos del usuario sólo dentro del
alcance autorizado, con revisión nueva y conservación de correcciones humanas;
no sobrescribir selecciones o actas cerradas. Documentar operación en el runbook
y resultados reales en BACKEND_IMPLEMENTATION_STATUS.md.

Orden de ejecución: referencia → reparación determinista → recuperación LLM
parcial → segunda lectura visual → revisión integrada → pruebas reales.
