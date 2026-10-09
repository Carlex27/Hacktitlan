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

El firewall de Windows debe admitir TCP al puerto configurado únicamente desde
la interfaz/perfil de Tailscale. PostgreSQL no debe publicarse en Tailscale ni
en Internet. El cliente consume sólo `http://<ip-tailscale>:8765/api/v1`.
Aplicar la regla como administrador con
`scripts/configure-tailscale-firewall.ps1 -TailscaleIPv4 <ip-tailscale>`.

## Validación

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
