# Clasificador local LIGIE - Capítulo 72

Proyecto para extraer certificados de materiales y determinar de forma
explicable una fracción arancelaria mexicana y su NICO dentro del capítulo 72.

## Estado actual

La fase de descubrimiento y normalización inicial está en curso. Ya existe una
extracción reproducible del PDF proporcionado en
`data/ligie/chapter-72/source-provided/` y una propuesta de arquitectura en
`docs/`.

El documento fuente está marcado `SIN VIGENCIA`; los datos extraídos no deben
usarse en operaciones aduaneras hasta ser contrastados con fuentes oficiales.

## Certificados de molino

La primera especificación ejecutable de extracción y normalización está en
[`docs/CERTIFICATE_EXTRACTION_RULES.md`](docs/CERTIFICATE_EXTRACTION_RULES.md).
Incluye casos dorados de `MOLINO 1` a `MOLINO 4`, normalización química exacta,
conteo dinámico de rollos, valores ditto, recubrimientos y validación contra
subtotales, piezas y pesos totales.

También existe una primera canalización determinista para formatos nuevos:
extrae texto digital, coordenadas y tablas, detecta semánticamente posibles
actas de molino, descubre encabezados mediante sinónimos y devuelve estados
explícitos de revisión u OCR. Existe un adaptador opcional para
PaddleOCR/PP-Structure, pero su descarga de modelos, calibración geométrica y
validación con el corpus real todavía están pendientes. No incorpora IA
generativa ni sustituye los normalizadores de los cuatro ejemplos conocidos.

```powershell
python -m unittest discover -s backend/tests -v
```

## Estructura de desarrollo

El repositorio ya contiene el esqueleto del backend, el frontend React/Tauri,
las pruebas, las reglas versionadas y el empaquetado. Las convenciones
obligatorias de arquitectura por componentes y calidad están en `AGENTS.md`.

La arquitectura objetivo utiliza PostgreSQL centralizado. Durante la
demostración, este equipo funcionará como servidor de base de datos y ambiente
principal de desarrollo; el segundo equipo consumirá la API backend mediante la
red privada de Tailscale. El frontend no accederá directamente a PostgreSQL.
Esta decisión es por ahora una especificación: la instalación y la configuración
se realizarán en una etapa posterior.

El alcance incluye un historial navegable por fecha, acta de molino, colada y
producto, además de la generación de documentos PDF/XLSX con la información
técnica, tipo de producto, fracción, NICO, evidencia y versión de reglas.
La exportación a Excel será opcional desde las vistas del historial y producirá
un libro profesional, autocontenido y relacionado internamente; los detalles se
encuentran en
[`docs/EXCEL_EXPORT_REQUIREMENTS.md`](docs/EXCEL_EXPORT_REQUIREMENTS.md).

La aplicación base no tiene un presupuesto fijo de RAM y puede operar sin GPU
dedicada. Los paquetes de OCR e IA local serán descargas opcionales ofrecidas
durante la instalación o posteriormente, siempre después de comprobar la
compatibilidad del equipo. La especificación está en
[`docs/LOCAL_MODELS_REQUIREMENTS.md`](docs/LOCAL_MODELS_REQUIREMENTS.md).
Cuando exista una GPU dedicada compatible, OCR e inferencia la utilizarán de
forma preferente, con selección automática del backend y respaldo por CPU.

Las decisiones operativas iniciales —sin usuarios, aprobación manual, archivos
centralizados, bloqueo sin servidor, volumen estimado, respaldos diarios,
reportes genéricos, fuente de reglas y Windows 11 x64— están consolidadas en
[`docs/PRODUCT_DECISIONS.md`](docs/PRODUCT_DECISIONS.md).

El plan ejecutable del backend y PostgreSQL está en
[`docs/BACKEND_DEVELOPMENT_PLAN.md`](docs/BACKEND_DEVELOPMENT_PLAN.md).
La secuencia detallada desde el estado actual hasta finalizar el backend está en
[`docs/BACKEND_COMPLETION_PLAN.md`](docs/BACKEND_COMPLETION_PLAN.md).
La instalación del servidor, migraciones, ejecución y respaldo se describen en
[`docs/BACKEND_RUNBOOK.md`](docs/BACKEND_RUNBOOK.md).
El avance verificable y lo pendiente por diseño están en
[`docs/BACKEND_IMPLEMENTATION_STATUS.md`](docs/BACKEND_IMPLEMENTATION_STATUS.md).
Las reglas, límites y comportamiento conservador del segundo hito están en
[`docs/CLASSIFICATION_ENGINE_RULES.md`](docs/CLASSIFICATION_ENGINE_RULES.md).

## Regenerar la extracción

```powershell
python tools/extract_chapter72.py
```

El script conserva filas crudas, catálogo normalizado, notas y un reporte de
calidad para permitir auditoría.
