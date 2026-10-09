# Operación local del backend

## Requisitos del servidor

- Windows 11 x64, Python 3.12–3.14 y `uv`.
- PostgreSQL 18 nativo, incluyendo `psql`, `pg_dump` y `pg_restore` en `PATH`.
- Tailscale conectado. PostgreSQL permanece en loopback; sólo la API escucha en
  la IP Tailscale del servidor.

## Preparación

1. Cambiar las contraseñas de ejemplo en `scripts/postgres/bootstrap.sql` y
   ejecutarlo con `psql -U postgres -f scripts/postgres/bootstrap.sql`.
2. Ejecutar `uv sync --all-groups` y copiar `.env.example` a `.env`.
3. Usar temporalmente la cuenta migradora en `HACKTITLAN_DATABASE_URL`, ejecutar
   `uv run alembic upgrade head` y después cambiar la URL a `hacktitlan_app`.
4. Configurar
   `HACKTITLAN_API_HOST` con la IP Tailscale y elegir una carpeta secundaria de
   respaldo distinta del disco principal.
5. Ejecutar `scripts/run-api.ps1` y `scripts/run-worker.ps1`.

Después de actualizar extracción/OCR, cerrar los workers anteriores antes de
iniciar el nuevo. Reiniciar sólo la API no actualiza el código cargado por los
workers. Comprobar sus PID, fecha de inicio y ruta con:

```powershell
Get-CimInstance Win32_Process |
  Where-Object { $_.Name -eq 'python.exe' -and $_.CommandLine -match 'backend.app.application.worker' } |
  Select-Object ProcessId, ParentProcessId, CreationDate, CommandLine
```

El lanzador Python puede tener un proceso hijo: contar árboles de procesos,
no filas. Esperar los trabajos activos antes de cerrar su worker. Verificar
después el `worker_id` del trabajo en PostgreSQL y reprocesar por la API para
crear una revisión nueva, conservando el acta y sus decisiones anteriores.

El firewall de Windows debe admitir TCP al puerto configurado únicamente desde
la interfaz/perfil de Tailscale. PostgreSQL no debe publicarse en Tailscale ni
en Internet. El cliente consume sólo `http://<ip-tailscale>:8765/api/v1`.
Aplicar la regla como administrador con
`scripts/configure-tailscale-firewall.ps1 -TailscaleIPv4 <ip-tailscale>`.

## Validación

### Exportar un acta a Excel

En el detalle del acta, Generar Excel solicita un reporte de consulta del acta
completa; Descargar Excel aparece al terminar. No exige aprobación: el archivo
indica los estados del acta y de la fracción/NICO de la ejecución seleccionada.
Elegir códigos no implica aprobarlos. Los rollos sin resultados aparecen como
pendientes de clasificación y las selecciones retiradas conservan su auditoría.

El flujo utiliza las operaciones de exportación documentadas en `/openapi.json`
y `/docs`. La API encola el trabajo; debe estar ejecutándose un worker. Reiniciar
la API y los workers tras actualizar para cargar los esquemas y el formato nuevo.
El Excel incluye resumen, actas, batches, coladas, composición, clasificación,
evidencia y auditoría, con filtros, encabezados congelados y estados con texto y
color. Exporta los datos disponibles y conserva ausentes como celdas vacías.

### Filtros del historial

`GET /api/v1/certificates` combina los filtros declarados en OpenAPI. La búsqueda
de acta admite número parcial, nombre original del archivo, ID o `Acta #ID`.
Las búsquedas textuales ignoran espacios exteriores y mayúsculas; `%` y `_`
se tratan literalmente. Colada y serie se buscan parcialmente; fracción admite
un prefijo con puntos o guiones y NICO es exacto. Los filtros de producto juntos
deben coincidir en el mismo rollo y la clasificación pertenece a la última
ejecución del acta, evitando coincidencias en decisiones anteriores.

Desde/Hasta incluyen ambos extremos y usan la fecha del acta: un acta sin fecha
queda fuera del intervalo. `date_basis=uploaded` permite consultar por fecha de
carga. La ordenación conserva la fecha de carga como respaldo para actas sin
fecha cuando no hay intervalo. Limpiar filtros vuelve al listado completo;
paginación y actualización conservan los filtros aplicados. Consultar el contrato
generado en `/openapi.json` o `/docs`.

### Eliminar un acta completa durante pruebas

Aplicar `uv run alembic upgrade head` con la cuenta migradora y reiniciar la API.
La migración `0009_certificate_deletion` concede `DELETE` a `hacktitlan_app`
en las tablas del acta; no cambia permisos de reglas ni respaldos.

Con `HACKTITLAN_ENVIRONMENT=development` o `test`, usar
`DELETE /api/v1/certificates/{certificate_id}` desde `/docs` o un cliente HTTP.
No recibe cuerpo, persona ni motivo. Consultar el contrato generado en
`/openapi.json` y la operación en Swagger; devuelve los identificadores del
acta y documento eliminados y `deleted: true`.

El borrado es definitivo: elimina documento, extracción, trabajos, coladas,
rollos, química, observaciones, correcciones, clasificaciones, selecciones,
aprobaciones, evidencias y archivos propios. También elimina las exportaciones
que incluyen el acta, incluso reportes con varias actas, y sus trabajos.
Conserva otras actas/revisiones, fabricantes, reglas y respaldos existentes.
Las revisiones posteriores pierden únicamente el enlace a la revisión borrada.
Los archivos compartidos por otros documentos o exportaciones se conservan.
El mismo PDF/XLSX puede cargarse de nuevo como un acta nueva.

En otros entornos responde 403 (`certificate_deletion_disabled`); si no existe,
404 (`not_found`); con trabajos o exportaciones en ejecución, 409
(`certificate_in_use`). Los trabajos en cola se eliminan junto con el acta.
El borrado bloquea brevemente escrituras mientras comprueba y elimina los datos.
Un fallo antes del commit revierte la base y restaura los archivos movidos.
Los archivos se retiran primero a `storage/.tmp` y se destruyen tras el commit;
una interrupción del proceso en ese intervalo puede dejar archivos allí y
requiere revisión manual. No elimina copias en respaldos.

La clasificación se ejecuta aun con baja confianza de extracción o incidencias
documentales. Se conservan las advertencias, los datos faltantes y las sugerencias
para revisión del personal; las incidencias bloqueantes mantienen el resultado
en `needs_review`, sin aprobarlo automáticamente. Después de actualizar el worker,
reclasificar las actas existentes para generar una nueva ejecución con sugerencias.

Si la laminación es el único dato pendiente, el motor evalúa frío y caliente
por separado. Sólo ofrece esas alternativas si ambas ramas resuelven una única
fracción/NICO y todos sus demás factores cumplen. Cada candidato conserva
`rolling` desconocido y un factor que indica la laminación que el operador debe
confirmar al elegirlo. La selección queda auditada; no cambia el dato extraído
ni aprueba automáticamente el acta. Si ambas ramas dan el mismo código, se
ofrece una sola opción. Otros datos pendientes o contradicciones impiden este
caso especial; no se completan elementos químicos ausentes con cero.

Excepción solicitada para zinc electrolítico: con dimensiones, presentación y
recubrimiento conocidos, y alguna química medida, pueden mostrarse sugerencias
provisionales aunque falten elementos para determinar la familia del acero.
Se conservan sólo los candidatos compatibles con ambos escenarios de
laminación, sin contradicciones conocidas. Cada opción deja explícitos los
elementos ausentes y exige confirmación de la familia y de la laminación por
el operador; no rellena química, no selecciona ni aprueba automáticamente.


Una ejecución aprobada conserva sus fracciones y NICO: `/api/v1/classification-results/{result_id}/select`
rechaza tanto sugerencias como capturas manuales con HTTP 409 (`run_already_approved`).
En actas abiertas, `POST /api/v1/classification-results/{result_id}/deselect` recibe
persona y motivo, retira la selección vigente y devuelve el rollo a `needs_review`.
Conserva las selecciones previas y registra la retirada en los detalles del resultado.
Las actas aprobadas rechazan también esta operación con 409.

### Extracción y verificación por campo con Ollama local

El worker puede consultar Ollama instalado en la misma computadora del backend.
La interfaz web no se conecta directamente al motor. No se agregan endpoints ni
dependencias Python; se utiliza la API HTTP local con la biblioteca estándar.
Aplicar `uv run alembic upgrade head` (migración `0008_field_verification`) y
reiniciar API y worker después de actualizar el código.

1. Instalar Ollama y descargar el modelo, por ejemplo `ollama pull qwen3.5:4b`.
2. Agregar a `.env`:

   ```dotenv
   HACKTITLAN_OLLAMA_ENABLED=true
   HACKTITLAN_OLLAMA_BASE_URL=http://127.0.0.1:11434
   HACKTITLAN_OLLAMA_MODEL=qwen3.5:4b
   HACKTITLAN_OLLAMA_TIMEOUT_SECONDS=60
   HACKTITLAN_OLLAMA_MAX_PAGE_CHARS=24000
   ```

3. Mantener Ollama en ejecución y reiniciar el worker. El nombre configurado debe
   coincidir con un modelo local descargado (`ollama list`). Cambiarlo no descarga
   el modelo automáticamente. Desactivar con `HACKTITLAN_OLLAMA_ENABLED=false`.
4. Desactivar funciones cloud en Ollama (`OLLAMA_NO_CLOUD=1` en el entorno del
   proceso Ollama y reiniciarlo). Esta variable pertenece a Ollama, no al backend.

Sólo se admiten servidores HTTP de loopback y nombres de modelos sin `cloud`.
Las solicitudes no usan proxies del entorno ni siguen redirecciones.
Después de leer el PDF y completar OCR, los adaptadores conocidos y la
extracción genérica envían sus observaciones a la verificación por campo. XLSX
y páginas que todavía requieren OCR no utilizan el modelo. Cada sección de
página incluye datos originales y normalizados, rollo/colada, texto, tablas,
coordenadas e identificadores. El esquema limita campos y citas a los enviados;
el backend rechaza respuestas incompletas, duplicadas y asociaciones no
comprobables. En modo texto exige evidencia literal. Si el modelo declara
capacidad `vision`, hay un PDF disponible y la página procede de OCR, la
verificación adjunta un recorte original con fila y encabezados; puede proponer
una lectura distinta del OCR, conservando ambas y la región citada. Las consultas
se dividen por rollo. Un fallo de renderizado vuelve a texto y deja `visual_error`.

Si no existe certificado extraído, una propuesta validada se persiste con
adaptador `ollama_local` y estado `needs_review`, y pasa también por verificación
por campo (resumen en `llm_assistance.verification`). Si ya existe un certificado,
se conserva y cada observación guarda su comparación en
`observations.verification_json`: `matches`, `discrepancy`, `not_verifiable` o
`error`. Se guardan valor literal, propuesta normalizada, unidad, página, celda
o bloque, encabezado, coordenadas y modelo. La comparación del backend prevalece
sobre la opinión del modelo: `13` bajo `C 10^-4` equivale a `0.0013 %`, aunque
la extracción original haya obtenido `0.13 %`.

Las propuestas comprobables cubren química con escala explícita y ancho/espesor
con unidades explícitas. Los demás campos se muestran como no verificables
mientras no tengan una regla segura de normalización y evidencia. Una celda
debe pertenecer a la columna citada y al rollo identificado por su encabezado.
La química de tablas sólo por colada requiere esa identificación; una colada
compartida no justifica usar la celda de otro rollo. Los bloques deben quedar
dentro de las coordenadas originales del campo. Las coordenadas de las celdas
son las del `TableRegion` disponible, sin inferir cajas individuales.

El resumen queda en `llm_assistance` de `documents.metadata_json` y
`extraction_runs.detection_json`; los campos quedan también en
`extraction_runs.normalized_json`. Discrepancias, campos no verificables o errores
producen `needs_review`. Se conservan verificaciones químicas por rollo aun cuando
sus porcentajes coincidan. No se sustituyen datos ni se aprueba por una coincidencia.

Cuando faltan dimensiones o elementos con encabezado/escala reconocible, se
intenta recuperación parcial por rollo (`llm_assistance.partial_recovery`). El
valor ausente sigue ausente: se guarda una propuesta en la observación para
aceptarla mediante la corrección auditada. Se registran errores por página y
rollo. No se reemplaza una propuesta visual existente por una recuperación textual.
Si varias páginas proponen valores distintos, el campo queda no verificable.

Lecturas OCR independientes y superpuestas de la misma celda pueden producir
una discrepancia con modelo `PaddleOCR`, incluso con Ollama desactivado. En
MOLINO 3, 39/0.39 se conserva y 33/0.33 se propone con su fuente y escala. Es una
corrección por revisar contra el PDF, no una selección automática de verdad.
La ausencia de texto permite consulta visual sólo si el rollo y el encabezado
delimitan una región. Una celda vacía o un símbolo sin origen comprobable queda
pendiente. `ocr_page_rotations` conserva orientación para los recortes visuales.

Para evaluar archivos reales sin crear actas ni aprobaciones en la base:

```powershell
uv run python scripts/evaluate_certificate_extraction.py "ruta/acta.pdf" --output tmp/evaluations/reporte.json --layouts tmp/evaluations/layouts
```

Se pueden pasar varios PDF. Agregar `--with-llm` para evaluar también Ollama.
El informe guarda resultado, evidencia, cantidad de productos y duración por
archivo; las capturas opcionales permiten reproducir los fallos del parser.
Un resultado `needs_review` con datos incompletos no equivale a extracción correcta
de todo el documento. Las pruebas de los cuatro PDF no cubren todos los formatos
posibles. El requisito de 8 GB de RAM fue retirado por el usuario; el consumo se
evalúa según el modelo y el equipo disponible, sin un presupuesto fijo.

En Extraído, abrir el detalle del rollo y Datos extraídos principales. La columna
Verificación local muestra el estado, la propuesta y las citas. Ver evidencia
abre la página del PDF; no resalta una celda. Revisar propuesta permite aceptar
una discrepancia con persona y motivo mediante el endpoint de correcciones
existente y `accept_verification=true`. El servidor usa la propuesta guardada,
preserva el dato anterior y registra auditoría; rechaza campos reemplazados o
sin propuesta válida. Recalcular las sugerencias después de corregir sus datos.
Los contratos se consultan en `/openapi.json` y `/docs`.

Ante un fallo, falta del modelo, JSON inválido o evidencia no comprobable se
conserva el resultado original y se registra una advertencia y el tipo de error
en la verificación y su resumen. El límite de entrada aplica al JSON de campos
y fuentes de cada sección; si se supera se marca esa sección como error sin
truncarla. Las demás secciones verificadas se conservan.
No se envían imágenes ni se intenta corregir OCR ilegible. El timeout aplica a
las operaciones HTTP por página; la cancelación se comprueba antes y después
de cada solicitud, por lo que una solicitud en curso puede tardar en terminar.

Pruebas sin instalar Ollama:

```powershell
uv run pytest backend/tests/unit/test_ollama_extraction.py backend/tests/unit/test_ollama_verification.py backend/tests/unit/test_certificate_extraction_service.py -q
```

La calidad y latencia reales requieren evaluar PDF revisados manualmente con el
modelo instalado y el hardware objetivo antes de activar el flujo en producción.

La aprobación del acta exige una selección humana de fracción y NICO para cada
producto de cada colada. La ejecución debe cubrir todos los productos actuales
del acta y cada colada debe tener productos incluidos; una cobertura incompleta
se rechaza con `classification_incomplete` (409), sin cambiar el estado del acta.

### Progreso de procesamiento

Después de guardar una extracción con productos, el worker genera una ejecución
de clasificación con hasta tres sugerencias de fracción y NICO por rollo.
Las opciones condicionales conservan sus datos faltantes y requieren revisión;
la selección humana y la aprobación siguen siendo pasos separados. El resultado
del trabajo incluye `classification_run_id`, consultable mediante los endpoints
de clasificación existentes. Si falla esta etapa, la extracción se conserva y
el trabajo termina en `needs_review` con `error_code=automatic_classification_failed`
y el motivo en `error_message`. Reiniciar el worker tras actualizar el código.
Las actas existentes pueden generar sus sugerencias mediante el endpoint de
reclasificación documentado en OpenAPI, sin volver a extraer el PDF.

El recibo de subida incluye `job_id`. Su avance se consulta en
`GET /api/v1/jobs/{job_id}`; el contrato tipado `JobEnvelope` se genera en
OpenAPI. La aplicación consulta cada segundo y deja de hacerlo ante un estado
terminal. El worker informa inicio (10), páginas OCR terminadas (hasta 90) y
preparación del guardado (95). El 100 sólo se publica junto con el estado final
en la transacción que guarda la extracción. `needs_review` y `needs_ocr` también
son finales: terminar el trabajo no significa aprobar los datos ni completar
OCR cuando falta el runtime.

El avance ocurre antes de inferir la página siguiente. La carga de modelos o
una página lenta pueden dejar el porcentaje fijo; no se simula avance ni se
estima el tiempo restante. Un reintento completo reinicia el porcentaje; el
fallback GPU/CPU del mismo intento mantiene el avance máximo alcanzado. Si la
conexión falla, la interfaz muestra el error y permite reanudar la consulta.

Pruebas del flujo:

```powershell
uv run pytest backend/tests/unit/test_ocr_runtime.py backend/tests/integration/test_processing_progress.py -q
node --test apps/desktop/tests/integration/certificateImportProgress.test.mjs apps/desktop/tests/unit/documentUpload.test.mjs
```

Las pruebas frontend ejecutan el hook y las llamadas HTTP con un simulador de
ciclo de hooks y temporizadores. El proyecto de escritorio todavía no incluye
el manifiesto ni el toolchain React/Tauri para validar el renderizado real.

### Importación de Excel

`POST /api/v1/documents` acepta PDF y XLSX mediante el mismo multipart `file`.
El original se guarda por SHA-256, conserva su extensión y se puede descargar
desde `/api/v1/documents/{document_id}/file`. El límite `HACKTITLAN_MAX_PDF_BYTES`
se aplica a ambos formatos; XLSX además admite hasta 200 MiB descomprimidos y
1,000,000 de celdas. Se rechazan libros inválidos, cifrados, macros y archivos
`.xls` antiguos. No se agregaron dependencias: se utiliza openpyxl existente.

El worker procesa XLSX directamente, sin OCR. Las tablas con encabezados
`MILL NO`, dimensiones y química se extraen por hoja y fila, incluyendo elementos
en columnas japonesas y nombres químicos variables por registro. Los valores
`有効桁` no se aplican como potencias a porcentajes ya decimales. El perfil
KIMITSU de MOLINOS GENERAL se reconoce por el nombre de hoja y sus encabezados:
la primera columna de cada par contiene la precisión y la segunda el porcentaje,
aunque sus etiquetas estén invertidas/repetidas. Se conserva la evidencia de la
celda del porcentaje y una advertencia para confirmar contra el certificado.
Los pares con precisión inválida quedan desconocidos; se conservan ceros
explícitos con precisión ausente. Otros perfiles ambiguos dejan la química
desconocida. `HEAT NO` y `CAST NO` identifican la colada; `COIL NO` el rollo.
Las unidades faltantes y los ceros usados como marcadores de longitud o ensayos
no se convierten en mediciones físicas. Las columnas FRACCION/NICO son datos
de la fuente y nunca sustituyen los resultados del motor.

`GET /api/v1/documents/{document_id}/spreadsheet`, documentado en OpenAPI, devuelve
las hojas y celdas originales, advertencias y registros de cartas de resistencia
por especificación. En estas cartas se conserva el operador (`<`, `>=`, etc.),
la unidad MPa y la celda ancla de los rangos combinados; no se crean productos ni
se vinculan automáticamente esas afirmaciones con rollos. Las fórmulas se
conservan como texto y no se ejecutan. Una hoja desconocida se conserva igualmente.

Todos los Excel terminan en `needs_review`. No se fusionan automáticamente
filas entre hojas ni certificados distintos dentro del libro: su identificador
interno corresponde a hoja/fila, y los números del origen son observaciones.
El contenedor del libro no inventa un número de certificado ni fabricante.
Las observaciones químicas se conservan por producto, incluso si coinciden sus
porcentajes. El flujo React permite seleccionar PDF/XLSX, enviarlos a la API y
ver los recibos o errores, conservando recibos previos si falla un archivo del
lote. El resultado se consulta actualizando la cola de revisión existente.
Las evidencias de Excel conservan la referencia de celda en `source_text` y
utilizan `fallback: original_file`, evitando tratar una hoja como página PDF.
Queda pendiente un visor de celdas. El frontend todavía no tiene manifiestos
ni toolchain de compilación; no se verificó la pantalla en una aplicación ejecutable.

Comprobación local: se leyeron sin modificar los tres archivos proporcionados:
DIGITALES (718 filas), GENERAL (383 filas), SPCC-RESISTENCIA (280 registros de
especificación). Los recuentos incluyen las hojas de análisis y no representan
productos únicos. Las pruebas portables usan ejemplos sintéticos de sus
estructuras y cubren carga, worker real, PostgreSQL, descarga y procedencia.

El PDF normativo proporcionado está incluido en
`data/ligie/chapter-72/source-provided/LIGIE-UNIFICADA-ACERO.pdf`.
`GET /api/v1/rule-sources/{source_hash}/file` sirve únicamente esa fuente
administrada. Su hash figura en `SOURCE.md`; una versión inexistente responde
404 y una alteración del archivo responde 409 (`rule_source_integrity_error`).
El cliente no envía rutas de archivos.

`GET /api/v1/evidence/{evidence_link_id}` conserva dos variantes en OpenAPI:
observación del acta y referencia normativa. Para la fuente normativa, las
referencias nuevas incluyen `file_url`, `page_number`, `bbox`, `source_text`,
`can_focus_region` y `fallback`. Los umbrales químicos apuntan a la página 7;
los factores de fracción y NICO apuntan a sus entradas del catálogo. Si falta
geometría, `fallback: full_page` exige mostrar la página completa.
Los enlaces históricos no se reescriben: reclasificar genera referencias nuevas.
Al empaquetar el backend deben incluirse el PDF y los JSON de esta carpeta.

La captura auditada existente de observaciones permite `stainless_series` con
`200`, `300`, `400` u `other`; `null` conserva un dato desconocido. No se acepta
un grado como `304` en ese campo ni se infiere la serie desde porcentajes sin
una regla respaldada. Informar solamente una cara del recubrimiento conserva
`coating_both_sides` desconocido; una cara expresamente con 0 demuestra que no
están recubiertas ambas.

```powershell
uv run pytest
uv run alembic current
Invoke-RestMethod http://127.0.0.1:8765/api/v1/health/ready
```

Las pruebas de integración requieren una base migrada llamada exactamente
`hacktitlan_test` y la variable `HACKTITLAN_TEST_DATABASE_URL`. No apuntar estas
pruebas a producción.

## Reiniciar datos para pruebas locales

Detener la API y el worker antes de ejecutar, desde la raíz del proyecto:

```powershell
.\scripts\reset-database.ps1 -DatabaseName hackaitlac
```

Usar el nombre exacto de la base configurada en `HACKTITLAN_DATABASE_URL`;
`hackaitlac` es el nombre de la instalación local actual. También se puede ejecutar
`uv run python -m backend.app.operations.reset_database --confirm-database hackaitlac`.
Después, volver a iniciar `scripts/run-api.ps1` y `scripts/run-worker.ps1`
y actualizar la aplicación para limpiar las selecciones anteriores.

El comando borra los registros de las tablas del esquema `public` y reinicia sus
identificadores en una transacción. Conserva `alembic_version` y `rule_sets`,
el esquema, los permisos, los archivos originales y los respaldos en disco.
Así se pueden volver a importar los mismos documentos. El borrado de registros
es irreversible; no genera un respaldo automático. Sólo admite PostgreSQL en
loopback con entorno `development` o `test`, exige confirmar el nombre de la base
y aborta si hay trabajos `running`, tablas ocupadas o relaciones externas que
impidan vaciarla. El usuario de conexión necesita permisos de `TRUNCATE` y de
reinicio de secuencias; la cuenta de aplicación habitual no los tiene.

## Respaldo y restauración

Ejecutar `scripts/install-backup-task.ps1` como administrador una vez. La tarea
corre a las 02:00 y `StartWhenAvailable` recupera una ejecución perdida. Conserva
7 respaldos diarios, 4 semanales y 12 mensuales, verifica el dump mediante
`pg_restore --list`, incluye archivos y reglas, y valida el hash de la segunda
copia.

Una exportación integral manual se genera con
`uv run python -m backend.app.operations.backup --kind manual`.

La restauración es deliberadamente local y manual. En una base vacía:

1. Crear una base vacía y preparar los roles y permisos. Configurar
   `HACKTITLAN_DATABASE_URL` para esa base, con el rol restaurador.
2. Elegir carpetas vacías para almacenamiento y reglas. Ejecutar:

   ```powershell
   uv run python -m backend.app.operations.restore C:\respaldos\backup_manual.zip --storage-root C:\recuperacion\storage --rules-root C:\recuperacion\rules
   ```

3. Exigir `verified: true`: el comando verifica hashes antes de escribir, ejecuta
   `pg_restore --single-transaction --no-owner --no-privileges` y compara conteos
   y archivos al terminar. No ejecutar migraciones antes de restaurar: la base
   debe estar vacía. El respaldo ya incluye `alembic_version`.
4. Aplicar permisos del rol de aplicación sobre tablas/secuencias restauradas,
   configurar el servicio con la base y almacenamiento recuperados, ubicar las
   reglas bajo las rutas del proyecto y validar `/api/v1/health/ready`.

Sólo restaurar ZIP de origen confiable: `pg_restore` ejecuta los objetos SQL del
respaldo. Los archivos se copian antes de restaurar la base. Si PostgreSQL falla,
su transacción revierte; las carpetas copiadas permanecen para diagnóstico y el
siguiente intento necesita destinos vacíos. El comando requiere el manifiesto
con conteos generado por el Hito 7; los ZIP anteriores requieren el procedimiento
manual de verificación de hashes y `pg_restore`.

Si la segunda copia falla, el registro queda `failed`, conserva ruta/hash/manifiesto
del primario y el comando devuelve error. Después de recuperar la unidad o el
espacio, reintentar sin generar otro dump:

```powershell
uv run python -m backend.app.operations.backup --retry-secondary C:\respaldos\backup_daily.zip
```

La copia se publica atómicamente tras verificar su hash; el registro vuelve a
`verified`. Almacenamiento, primario y secundario deben usar carpetas independientes,
sin anidarse. Configurar el secundario en otra unidad para tolerar la pérdida del
disco primario; las pruebas de desarrollo usan carpetas del mismo disco.

La programación usa la hora local de Windows. Si falta respaldo de la semana ISO
o del mes actual, lo genera en la siguiente ejecución disponible, aunque Windows
haya estado apagado el lunes o el día primero. No reconstruye períodos pasados.
El script propaga el código de salida de Python al Programador de tareas.

No existe endpoint remoto de restauración.

## Medición de volumen del Hito 7

Configurar `HACKTITLAN_TEST_DATABASE_URL` para `hacktitlan_test`, con permisos de
crear/eliminar bases desechables. No usar credenciales de producción. PostgreSQL
18, `pg_dump`, `pg_restore` y `uv` deben estar disponibles en `PATH`.

```powershell
uv run python -m backend.app.operations.capacity --output tmp/hito7/capacity.json
uv run python -m backend.app.operations.capacity --ocr-pdf C:\corpus\acta-escaneada.pdf --output tmp/hito7/capacity-ocr.json
```

La herramienta crea bases aleatorias `hacktitlan_hito7_*`, aplica migraciones,
siembra 18,250 actas y 273,750 coladas/rollos, captura planes SQL, mide consultas,
exportaciones y un worker separado, respalda y restaura, compara conteos/hashes
y elimina únicamente las bases que acaba de crear. Conserva el JSON y los archivos
de evidencia bajo `tmp/hito7`. `--certificates 55 --samples 1` permite verificar
el recorrido sin repetir la medición completa.

La carga diaria de diez documentos y la ráfaga de treinta usan una extracción
normalizada controlada. No son mediciones OCR. El dataset histórico comparte un
PDF pequeño, un elemento químico y un candidato por rollo; no representa el consumo
de disco de cinco años de PDF reales. La API se mide mediante TestClient, sin TCP
ni Tailscale. CPU/RAM/E/S corresponden al proceso worker; no son el consumo total
de PostgreSQL ni del servidor. Para OCR, suministrar un PDF escaneado legible y
el runtime/modelos instalados. El JSON conserva pendientes los objetivos de
latencia y la aceptación del servidor; no inventa límites ni aprobación.

## Consultas y reportes del Hito 6

Consultar los contratos vigentes en `/openapi.json` o `/docs`.
`GET /api/v1/certificates` valida `processing_status` con los estados declarados
en OpenAPI. Un rango de fechas invertido devuelve HTTP 400 con
`invalid_date_range`; un cursor inválido devuelve `invalid_cursor`.
La paginación keyset conserva el orden de los registros originales bajo
inserciones, pero no crea una instantánea ni cubre cambios de la fecha de ordenación.

`POST /api/v1/exports` exige IDs positivos. Para `official=true`, cada acta debe
estar aprobada y tener una ejecución elegida aprobada. Sin IDs explícitos se
elige la última ejecución de cada acta; una última ejecución pendiente bloquea
el reporte aunque exista una anterior aprobada. La aprobación incompleta produce
HTTP 409 con `official_export_requires_approval` antes de crear el trabajo.
Los IDs resueltos se guardan en el alcance y el worker vuelve a validar su
aprobación al generar el libro. Los filtros guardados son metadatos de auditoría;
el alcance efectivo procede de los IDs seleccionados.

Los reportes por coladas incluyen sólo sus rollos, resultados y correcciones,
además de la evidencia general del acta. Texto externo permanece como texto,
sin ejecutarse como fórmula. La ausencia de evidencia se muestra sin hipervínculo.
# Reprocesamiento sin duplicados

`GET /api/v1/document-reviews` devuelve únicamente la última revisión de cada
PDF. Cada elemento incluye `revision_number`, `active_job_id` y `can_reprocess`.
El frontend debe deshabilitar el reprocesamiento cuando `can_reprocess` sea falso.

`POST /api/v1/certificates/{certificate_id}/reprocess`, con
`from_stage: "extraction"`, responde HTTP 409 con código
`reprocess_in_progress` si cualquier revisión del mismo PDF tiene una extracción
`queued` o `running`. `error.details.job_id` identifica ese trabajo.
El bloqueo se serializa en PostgreSQL sobre el archivo almacenado.
Al terminar el trabajo puede solicitarse otra extracción. Incluso al enviar un
ID antiguo, la nueva revisión parte de la última revisión disponible.
Las revisiones históricas siguen accesibles por ID.
# Extracción de proveedores y formatos nuevos

El lector OCR procesa PDF escaneados y conserva texto, confianza y coordenadas
en páginas orientadas. Las tablas HTML respetan `rowspan` y `colspan`.
Cuando una línea mezcla varias columnas, una segunda lectura utiliza celdas
delimitadas por encabezados y líneas de tabla, con imágenes de mayor resolución.

El extractor genérico reconoce encabezados multilingües, dimensiones combinadas,
pesos netos/brutos, propiedades mecánicas, recubrimientos y escalas químicas.
Un perfil conocido sin adaptador utilizable también pasa por este extractor.
No se necesita registrar cada proveedor. Una química sin escala reconocible
permanece como evidencia pendiente; no se interpreta automáticamente como porcentaje.

La extracción genérica termina en `needs_review`, aunque haya guardado rollos.
Esto requiere verificar los valores OCR antes de aprobar o clasificar. Los campos
ilegibles quedan ausentes; no se convierten en cero. Se conservan bloques no
interpretados y motivos en la ejecución de extracción.

Las pruebas `test_real_mill_ocr_layouts.py` usan capturas del OCR real de los cuatro
PDF de referencia, no sus archivos `.raw.json`. Comprueban 6, 1, 11 y 6 rollos,
identificadores y pesos, junto con campos químicos y mecánicos seleccionados.
Estas capturas prueban el parser sin exigir ejecutar los modelos en cada prueba;
una actualización de Paddle requiere volver a verificar los PDF reales.

Para POSCO EG, `Commodity` se conserva como descripción del producto y
`Spec & Type` como especificación; `Grade Total` es un subtotal, no un grado.
Las lecturas OCR superpuestas de un identificador se combinan por geometría
para evitar rollos duplicados. En química marcada `%` se prioriza la alineación
con el encabezado para evitar recortes que pierdan el último decimal.
La captura `molino-4-refined.json` comprueba seis rollos, dos coladas y cinco
elementos por rollo con la segunda lectura de celdas del PDF real. Reiniciar el
worker y reprocesar la extracción de las actas anteriores para aplicar el cambio.

## Unidades y porcentajes en extracción genérica

Las unidades dimensionales explícitas en la celda o en su encabezado se convierten
sin modificar el valor original: mm, cm, m, pulgadas (`in`, `inch`, `"`) y pies
(`ft`, `feet`, `'`). Se admiten fracciones como `1/8 in` y `1 1/2 in`.
Espesor y ancho se almacenan en mm; largo permanece en m según el modelo existente.
Una pulgada equivale a 25.4 mm y un pie a 304.8 mm. Sin unidad explícita se mantiene
la convención existente de mm para espesor/ancho y m para largo independiente.
Las dimensiones imperiales combinadas sin etiquetas de orden se conservan como
evidencia: no se asume que `ancho × espesor` significa `espesor × ancho`.

Una composición marcada `%` ya es porcentaje y no se divide. Las escalas explícitas
se aplican una vez, por elemento: `×1000` o `/1000` implica dividir por 1000;
`10^-3` implica multiplicar por 0.001; `ppm` se convierte a porcentaje multiplicando
por 0.0001. Se admiten potencias con superíndices. Nunca se deduce una escala
por el tamaño del número. Los datos ambiguos requieren revisión humana.

### Revisión web y borradores

La UI organiza carga y revisión en una sección e historial en otra. El historial utiliza los filtros declarados en OpenAPI de `GET /api/v1/certificates`, con paginación y filtros en el servidor. Fracción y NICO se consultan sobre los códigos que el backend conserva en resultados de clasificación; no se buscan dentro de candidatos todavía no seleccionados.

`POST /api/v1/classification-runs/{run_id}/draft` guarda una ejecución pendiente o rechazada como borrador con persona y motivo, conserva las selecciones y registra la transición. Guardar un borrador que ya es borrador es idempotente. Una ejecución aprobada no puede volver a borrador. Reiniciar la API al desplegar esta ruta. Consultar su contrato y errores en `/openapi.json` o `/docs`.

El procesamiento continúa al cambiar de sección en la web; el historial permite recuperar los datos persistidos. Los campos de auditoría aún no enviados no se guardan al navegar. El borrador no aprueba ni valida condiciones pendientes.

Las actas sin ejecuciones pueden solicitar su clasificación desde la UI mediante `POST /api/v1/certificates/{certificate_id}/reclassify`; el contrato tipado y el recibo del trabajo están en OpenAPI. No se repite la extracción. El worker debe estar activo para terminar el trabajo.

La acción “Descartar del historial” utiliza el archivo lógico existente (`POST /api/v1/documents/{document_id}/archive`) con persona y motivo. No elimina datos ni originales. La misma vista permite restaurar el documento antes de salir; fuera de ella, un operador puede restaurarlo con esa ruta y `archived=false`, según el contrato de `/docs`.

### Captura manual de clasificación

Aplicar `uv run alembic upgrade head` (migración `0007_manual_classification`) y reiniciar la API si no usa recarga automática. La migración permite conservar capturas manuales junto a las sugerencias originales; no elimina registros. Un downgrade falla si existen rangos superiores a tres, para evitar perder auditoría.

El contrato vigente se consulta en `/openapi.json` y `/docs`: `/api/v1/classification-results/{result_id}/select` acepta un candidato existente o una fracción/NICO manuales, junto a persona y motivo. La captura manual valida formato y conserva la justificación y selecciones anteriores; no consulta automáticamente la vigencia normativa del código. Las ejecuciones aprobadas rechazan cambios manuales.

En la web, el dictamen envía persona Administrador y un motivo fijo sin campos editables. Es una identificación operativa compartida, no una cuenta autenticada ni una firma individual. La captura manual conserva su justificación escrita. El historial de auditoría permanece en el backend aunque se retire la pestaña del detalle del acta.

La confirmación del acta (`POST /api/v1/classification-runs/{run_id}/approve`) cierra la revisión humana registrada mediante las selecciones de cada rollo. Exige cobertura completa de productos y coladas, selección, fracción y NICO; conserva datos faltantes y factores desconocidos del motor, y bloquea contradicciones. El cliente envía persona y motivo fijos por decisión del usuario.

El detalle de acta expone el nombre original del archivo en OpenAPI; la navegación web usa ese nombre para archivos XLSX, conservando el número extraído del certificado.

El listado de actas publica también el nombre original del archivo mediante su esquema OpenAPI para presentar los XLSX por nombre en el historial.

La cola de revisión documental incluye el nombre original del archivo en su esquema OpenAPI para mostrar los XLSX por nombre.

## Omitir portadas ArcelorMittal en OCR

El lector escaneado consulta sólo el encabezado a 120 dpi con el OCR compartido,
sin análisis de tablas. Omite el procesamiento completo únicamente cuando reconoce
ArcelorMittal y el título `Inspection Document Cover Sheet`. Si la lectura falla,
es incierta o la página está girada, conserva el OCR completo. No usa posiciones
fijas: admite varias portadas y coladas dentro del mismo PDF.

Las páginas de química, dimensiones, recubrimiento, ensayos y especificaciones
siguen procesándose. El PDF original y la numeración de evidencia se conservan;
`document.ingestion.ocr_skipped_pages` registra página y motivo. Una portada
omitida no se interpreta como una página pendiente de OCR. Reiniciar el worker
para cargar este cambio. El ahorro depende de las portadas reconocidas y del
coste de la lectura ligera; no supone omitir todas las páginas de un fabricante.

## Biblioteca de formatos: borradores y pruebas

Aplicar `uv run alembic upgrade head` con la cuenta migradora (hasta 0011_format_activation)
y reiniciar API y worker después de terminar trabajos activos. La migración añade
tablas de biblioteca, layouts preparados y pruebas; no convierte borradores en
plantillas activas ni reprocesa actas. Validada en hacktitlan_test; la aplicación a
otras instancias forma parte del despliegue. Un downgrade elimina los nuevos
artefactos y sus jobs; no ejecutarlo para una reversión que deba conservarlos.

Consultar solicitudes y respuestas en `/openapi.json` o `/docs`, sección
Certificate format drafts. El flujo es crear formato, editar su borrador,
preparar el documento mediante layout-jobs, consultar progreso con el endpoint
de jobs existente y solicitar una prueba sobre el layout preparado. Un layout
se consulta tanto por documento (último) como por id (exacto usado por la prueba).
Las imágenes por página se generan con el tamaño/orientación del layout.

Las ediciones exigen la revisión esperada; un conflicto devuelve 409 y requiere
recargar el borrador. La prueba conserva configuración, revisión y hash del
extractor aunque el borrador se edite después. current_revision indica si todavía
corresponde al borrador actual. Las versiones activas y retiradas son inmutables;
para cambiarlas se crea una versión nueva.

La preparación usa el lector digital/OCR configurado. Si falta lectura, conserva
needs_ocr; no presenta una página ilegible como vacía. Las tareas nuevas admiten
cancelación en cola y en ejecución mediante el endpoint existente; OCR se
interrumpe en los puntos de comprobación del lector. Errores de infraestructura
usan failed y los reintentos existentes, no needs_review.

La vista previa requiere unidades y escalas explícitas, tablas detectadas
completas y encabezados configurados. No reconstruye automáticamente tablas
complejas ni une filas sin clave. success significa que terminó la extracción
configurada, no aprobación documental ni validación arancelaria. Páginas no
cubiertas con datos, claves duplicadas y lecturas ambiguas requieren revisión.
Estas pruebas no llaman a persistencia de actas ni al clasificador. Borrar un
acta en desarrollo elimina sus layouts y pruebas, conservando sus formatos.

### Editor web y activación

Entrar en Biblioteca de formatos o Configurar formato desde un acta PDF. Capturar
un nombre de formato, crear/abrir un borrador, elegir documento y preparar páginas.
Por decisión del usuario, el frontend envía Administrador y un motivo fijo sin
campos visibles de persona/motivo.
Seleccionar una zona arrastrando, eligiendo texto/tabla con teclado o ajustando
porcentajes. Asignar campos o encabezados de columnas y guardar/probar. La prueba
compara originales, normalizados, evidencia y diagnósticos sin modificar el acta.
Ver PDF de esta prueba recupera su layout exacto antes de confirmar valores.

La activación exige dos textos estables distintos en regiones orientadas y tres
PDFs con hashes distintos, pruebas success confirmadas por una persona y hash,
revisión y extractor actuales. No se aceptan pruebas obsoletas ni resultados con
incidencias. Es una validación inicial, no una garantía de generalización. La
confirmación no aprueba actas ni decisiones arancelarias. Los contratos de
confirmación, activate, retire y format_version_id están en OpenAPI.

Como máximo una versión activa por formato; activar una nueva retira la anterior
atómicamente. Los cambios registran persona, motivo, fecha y pruebas/hash de
validación. Retirar evita la selección futura y conserva trabajos ya encolados.
Los jobs nuevos fijan candidatos/configuración/hash antes de encolarse. Un
adaptador calibrado tiene prioridad en modo automático; varias plantillas
coincidentes generan revisión. Sin coincidencia se conserva el flujo genérico.
La selección explícita al reprocesar exige compatibilidad y crea otra revisión.
Todas las extracciones de usuario quedan needs_review; nunca aprueban el acta.

Si cambian los archivos del extractor, una prueba/trabajo con su hash anterior
se rechaza y debe volver a encolarse. Los trabajos encolados antes de esta entrega
mantienen su comportamiento original. Una plantilla validada con un extractor
anterior deja de ser candidata automática; crear/probar/activar una versión
nueva antes de volver a usarla explícitamente. current_revision considera también
el hash del extractor vigente. La biblioteca usa el modelo de confianza
local existente: atribución de persona/motivo no es autenticación. Mantener API
en loopback; un despliegue compartido/remoto necesita autorización real antes de
exponer edición/activación.

No ejecutar migraciones a ciegas cuando alembic_version esté vacío y existan
tablas: verificar primero el esquema y recuperar su revisión de origen. No usar
stamp head para omitir migraciones. 0011 sólo se validó en hacktitlan_test; la
base de desarrollo no se modificó. Su downgrade rechaza versiones activadas o
retiradas para no borrar historia silenciosamente.
