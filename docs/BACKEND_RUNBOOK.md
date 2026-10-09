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

1. Extraer el ZIP y comprobar los hashes de `manifest.json`.
2. Ejecutar `pg_restore --list database.dump`.
3. Restaurar con una cuenta administradora:
   `pg_restore --clean --if-exists --no-owner --dbname hacktitlan database.dump`.
4. Copiar `storage/` a la ruta configurada y validar `/health/ready`.

No existe endpoint remoto de restauración.
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
