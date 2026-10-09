# Hacktitlan — Clasificador de acero LIGIE, capítulo 72

Hacktitlan es un proyecto realizado por el **Equipo ZankaTec del Instituto
Tecnológico de la Costa Grande**. Ayuda a revisar certificados de materiales y
proponer una clasificación arancelaria mexicana para productos de acero,
con datos técnicos y evidencia que permitan entender cada resultado.

El programa reúne en una interfaz web la carga de actas de molino, la consulta
de sus coladas y rollos, la revisión de información extraída y la selección de
una fracción arancelaria y su NICO (Número de Identificación Comercial).
La clasificación se apoya en reglas del capítulo 72 de la LIGIE (Ley de los
Impuestos Generales de Importación y de Exportación), con un motor enfocado
actualmente en productos laminados planos.

## ¿Qué hace el programa?

- **Importa documentos:** recibe certificados en PDF y archivos XLSX, conserva
  los originales y muestra el progreso de procesamiento.
- **Extrae información técnica:** identifica, según el formato y la legibilidad
  del documento, coladas, rollos, composición química, dimensiones, pesos,
  recubrimientos y propiedades mecánicas. Puede utilizar OCR para PDFs escaneados.
- **Organiza y valida los datos:** presenta los productos por colada, conserva
  valores originales y normalizados, y señala datos faltantes, lecturas dudosas
  o contradicciones para revisión.
- **Propone fracciones y NICO:** evalúa los datos disponibles mediante reglas
  deterministas y presenta candidatos con sus factores, fundamentos y evidencia.
- **Permite la revisión humana:** ofrece consulta de evidencia, correcciones
  auditadas, selección de sugerencias y captura manual de clasificación con
  justificación, antes de aprobar el acta.
- **Conserva un historial:** permite buscar actas y filtrar por fecha, colada,
  rollo y clasificación, manteniendo las revisiones y decisiones registradas.
- **Exporta información a Excel:** genera reportes XLSX con datos técnicos,
  clasificación y trazabilidad, distinguiendo resultados preliminares y aprobados.

## Flujo de uso

1. Cargar el certificado y esperar su procesamiento.
2. Consultar las coladas y rollos identificados y revisar los datos extraídos.
3. Examinar las sugerencias de clasificación y la evidencia que las respalda.
4. Corregir los datos que lo requieran y confirmar la fracción y el NICO de cada rollo.
5. Aprobar la revisión del acta y consultar o exportar los resultados desde el historial.

Una sugerencia del motor no equivale a una aprobación humana. Si el documento
no aporta información suficiente, el sistema conserva la incertidumbre y
solicita revisión; un dato ausente no se convierte en cero.

## Estado y alcance

El proyecto está en desarrollo. Utiliza una interfaz React en entorno web,
un servicio backend en Python/FastAPI y almacenamiento en PostgreSQL. La
interfaz consume la API del servicio; no accede directamente a la base de datos.

La extracción depende del formato y la calidad de cada certificado. El OCR y la
asistencia local de extracción con Ollama son componentes opcionales; sus
resultados requieren revisión y no sustituyen las reglas de clasificación.

El catálogo fuente proporcionado está marcado **`SIN VIGENCIA`**. Los resultados
deben contrastarse con fuentes oficiales vigentes antes de utilizarse en
operaciones aduaneras. El programa es una herramienta de apoyo a la revisión,
no una verificación automática de vigencia normativa.

El avance verificable y las limitaciones de implementación se mantienen en
[Estado del backend](docs/BACKEND_IMPLEMENTATION_STATUS.md).

## Documentación del proyecto

- [Producto y flujo de trabajo](PRODUCT.md).
- [Reglas de extracción de certificados](docs/CERTIFICATE_EXTRACTION_RULES.md).
- [Reglas del motor de clasificación](docs/CLASSIFICATION_ENGINE_RULES.md).
- [Instalación, ejecución y operación del backend](docs/BACKEND_RUNBOOK.md).
- [Plan de desarrollo](docs/BACKEND_DEVELOPMENT_PLAN.md) y
  [plan de finalización del backend](docs/BACKEND_COMPLETION_PLAN.md).
- [Requisitos de exportación a Excel](docs/EXCEL_EXPORT_REQUIREMENTS.md).
- [Requisitos de modelos locales](docs/LOCAL_MODELS_REQUIREMENTS.md).
- [Decisiones operativas](docs/PRODUCT_DECISIONS.md).
- [Convenciones de desarrollo](AGENTS.md).

Los contratos de la API se consultan en `/openapi.json`, `/docs` o `/redoc` con
el backend en ejecución.

## Herramientas de desarrollo

Para ejecutar las pruebas unitarias del backend:

```powershell
python -m unittest discover -s backend/tests -v
```

Para regenerar la extracción del catálogo fuente del capítulo 72:

```powershell
python tools/extract_chapter72.py
```

La extracción conserva filas crudas, catálogo normalizado, notas y un reporte
de calidad para permitir auditoría.
