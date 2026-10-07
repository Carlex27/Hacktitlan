# Arquitectura propuesta

## 1. Decisión principal

Usar una aplicación de escritorio Tauri con interfaz React y un servicio Python
local empaquetado como `sidecar`. El clasificador será determinista y el módulo
documental sólo producirá datos estructurados con evidencia.

```text
PDF -> extracción/OCR -> normalización -> validación -> motor de reglas
    -> fracción + NICO + explicación -> reporte y auditoría
```

## 2. Tecnologías

| Capa | Tecnología | Motivo |
|---|---|---|
| Escritorio | Tauri 2 | Instalador pequeño, acceso seguro a archivos y procesos locales |
| Interfaz | React + TypeScript + Vite | Formularios, tablas y revisión visual mantenibles |
| Componentes | shadcn/ui o Mantine | UI local consistente y accesible |
| Servicio local | Python 3.12 + FastAPI | Ecosistema sólido para PDF, OCR y reglas |
| Modelos | Pydantic | Validación estricta y esquema JSON versionado |
| PDF digital | pdfplumber + pypdfium2 | Tablas, texto, coordenadas y renderizado |
| OCR | PaddleOCR/PP-Structure | Inglés, chino y estructura tabular de forma local |
| Reglas | Evaluador propio sobre JSON/YAML | Operadores legales exactos, versionado y explicación |
| Base de datos | PostgreSQL + migraciones Alembic | Persistencia centralizada y acceso concurrente desde varios equipos |
| Red privada de demostración | Tailscale | Conectar el equipo cliente al servidor sin exponer PostgreSQL a Internet |
| Reportes | openpyxl + ReportLab | XLSX y PDF generados localmente |
| Pruebas | pytest + Hypothesis; Vitest/Playwright | Fronteras químicas, integración y UI |
| Empaquetado Python | PyInstaller | Sidecar autocontenido para Windows |
| Instalador | Tauri Bundler (MSI/NSIS) | Una sola instalación |

## 3. PostgreSQL central mediante Tailscale

PostgreSQL es la base de datos oficial del proyecto. Para la demostración y el
desarrollo principal se usará la siguiente topología:

```text
Equipo principal
├─ Aplicación y API backend principal
├─ PostgreSQL
└─ Tailscale
        ↕ red privada
Equipo secundario
├─ Aplicación cliente
└─ Tailscale
```

- El equipo principal funciona como servidor de PostgreSQL y ambiente principal
  de desarrollo.
- El equipo secundario consume la API backend del equipo principal mediante la
  red privada de Tailscale. El frontend nunca se conecta directamente a
  PostgreSQL.
- Sólo el backend posee credenciales de PostgreSQL y aplica autorización,
  validación, auditoría y reglas de negocio.
- PostgreSQL no debe exponerse directamente a Internet ni abrirse en el router.
- La conexión de la aplicación se configura mediante variables o configuración
  segura; las credenciales no se guardan en el repositorio ni en el frontend.
- Cada equipo o servicio debe usar un usuario de base de datos con los permisos
  mínimos necesarios.
- Las migraciones de esquema se ejecutan de forma controlada desde el equipo
  principal. Los clientes no modifican el esquema al iniciar.
- La demostración depende de que el equipo principal, PostgreSQL y Tailscale
  estén disponibles. La interfaz debe distinguir un error de conexión de un
  error de procesamiento documental.
- Debe existir una estrategia de respaldo y restauración antes de almacenar
  documentos o clasificaciones de operación.

SQLite deja de formar parte de la arquitectura objetivo. El dominio y los casos
de uso deben continuar separados del adaptador PostgreSQL para conservar pruebas
aisladas y evitar reglas de negocio dentro de consultas o modelos de persistencia.

## 4. Componentes

### `document_ingestion`

Detecta si hay capa de texto, renderiza páginas, ejecuta OCR si hace falta y
produce bloques con texto, tablas, página y coordenadas.

### `certificate_parser`

Identifica proveedor y plantilla, segmenta productos y mapea sinónimos como
`C`, `Carbon`, `碳` a un identificador canónico. No decide la fracción.

### `normalization`

Convierte porcentajes, milímetros, megapascales, unidades y nombres de elementos.
Preserva valor original y valor normalizado.

### `classification_engine`

Evalúa un grafo versionado:

1. pertenencia al capítulo 72;
2. familia metalúrgica;
3. forma y proceso;
4. partida y subpartida;
5. fracción;
6. NICO;
7. validación de unicidad.

Cada nodo devuelve `matched`, `not_matched`, `unknown` o `conflict`. El motor
nunca convierte `unknown` en `false`.

### `explanation`

Registra regla, operador, umbral, valor observado, evidencia y resultado. Esto
permite reconstruir por qué se eligió o descartó cada rama.

### `rule_registry`

Maneja versiones con `valid_from`, `valid_to`, hash de fuente y estado
`draft/approved/retired`. Una clasificación siempre apunta a una versión exacta.

### `reporting`

Genera una fila por producto o rollo y un anexo con decisiones, advertencias y
evidencia.

Debe generar también un documento de clasificación agrupado por acta y colada
que incluya datos del acta, composición, rollos asociados, tipo de producto,
fracción, NICO, estado de revisión, versión de reglas y evidencia utilizada. La
salida inicial debe admitir PDF y XLSX; CSV se reserva para exportación tabular.

La exportación XLSX es generada por el backend como una fotografía auditable,
sin macros ni conexiones externas. Debe contener tablas relacionadas por
identificadores estables, hipervínculos internos, filtros, formatos de unidades
y hojas separadas para resumen, actas, coladas, rollos, composición,
clasificación, evidencia y auditoría. Su especificación detallada está en
[`EXCEL_EXPORT_REQUIREMENTS.md`](EXCEL_EXPORT_REQUIREMENTS.md).

La fracción y el NICO pertenecen al resultado de clasificación de cada producto
o rollo. Una vista agrupada por colada sólo puede mostrar un único resultado
resumido cuando todos sus productos coincidan; en caso contrario debe mostrar
los distintos resultados sin elegir uno arbitrariamente.

### `historical_records`

Expone consultas paginadas y detalle histórico sin duplicar reglas de negocio.
Permite navegar por fecha, acta, colada y producto, y conserva enlaces hacia el
PDF original, observaciones, ejecuciones de clasificación, correcciones y
documentos generados.

## 5. Modelo de datos mínimo

- `documents`: archivo, hash, idioma, estado, fecha del acta, fecha de carga y
  metadatos del fabricante.
- `document_pages`: texto, imagen y estado OCR.
- `mill_certificates`: número de acta, fabricante y relación con el documento
  original.
- `heats`: colada, composición compartida, propiedades aplicables y relación con
  el acta. El número de colada no se considera globalmente único.
- `products`: rollo, lote o producto y relación con su acta y colada.
- `observations`: campo, valor original, valor normalizado, unidad, confianza,
  página y coordenadas.
- `chemical_compositions`: elemento y porcentaje con alcance explícito de
  colada o producto, según lo declarado por el acta.
- `physical_properties`: ancho, espesor, diámetro, forma y enrollado.
- `mechanical_properties`: límite elástico y demás ensayos.
- `process_properties`: caliente/frío, decapado, revestimiento y tratamientos.
- `rule_sets`: versión, vigencia, fuente, hash y aprobación.
- `rules`: predicados y enlaces del grafo.
- `tariff_entries`: partida, subpartida, fracción, NICO y descripción.
- `classification_runs`: entrada, versión, resultado y estado.
- `classification_results`: tipo de producto, fracción, NICO y descripción por
  producto para cada ejecución.
- `decision_steps`: explicación de cada evaluación.
- `manual_overrides`: cambio, motivo, usuario y sello de tiempo.
- `exports`: formato, ubicación, hash, fecha y ejecución usada por el reporte.

## 6. Consultas históricas obligatorias

El backend debe proporcionar consultas paginadas y filtros combinables para:

- registros por día o rango, distinguiendo fecha del acta y fecha de carga;
- actas por número, fabricante, estado de procesamiento o fecha;
- coladas por número, fabricante, acta, tipo de producto, fracción o NICO;
- rollos y productos asociados a una colada;
- detalle completo de una colada: composición, propiedades, rollos, evidencia,
  clasificaciones, correcciones y documentos generados;
- historial de ejecuciones para no sobrescribir una clasificación anterior
  cuando cambien los datos o la versión de reglas.

Las listas deben usar paginación y ordenamiento en el backend. El frontend sólo
envía filtros y presenta resultados; no descarga el historial completo para
filtrarlo localmente.

## 7. Contrato canónico de entrada

```json
{
  "product_id": "coil-001",
  "composition_pct": {"C": 0.08, "Cr": 18.1, "Ni": 8.2},
  "form": "flat_rolled",
  "coiled": true,
  "rolling": "cold",
  "pickled": false,
  "coating": "none",
  "width_mm": 1219.2,
  "thickness_mm": 1.2,
  "yield_strength_mpa": 310,
  "standard": "ASTM A240",
  "grade": "304",
  "intended_use": null,
  "evidence": []
}
```

Los valores `null` significan desconocido; no deben activar una regla negativa.

## 8. Estructura objetivo del repositorio

```text
Hacktitlan/
├─ apps/
│  └─ desktop/
│     ├─ src/                    # React/TypeScript
│     ├─ src-tauri/              # shell, permisos e instalador
│     └─ tests/
├─ backend/
│  ├─ app/
│  │  ├─ api/                    # endpoints locales
│  │  ├─ domain/                 # entidades y estados
│  │  ├─ application/            # casos de uso
│  │  ├─ document_ingestion/
│  │  ├─ certificate_parser/
│  │  ├─ normalization/
│  │  ├─ classification_engine/
│  │  ├─ rule_registry/
│  │  ├─ reporting/
│  │  └─ infrastructure/         # PostgreSQL, archivos, red y OCR
│  └─ tests/
│     ├─ unit/
│     ├─ integration/
│     ├─ boundaries/
│     └─ golden/
├─ rules/
│  └─ chapter-72/
│     └─ VERSION/
│        ├─ manifest.json
│        ├─ decision-graph.json
│        ├─ tariff-catalog.json
│        └─ tests.json
├─ data/
│  ├─ ligie/                     # fuentes y extracciones
│  └─ samples/                   # sólo ejemplos anonimizados
├─ docs/
├─ tools/                        # extracción y validación de fuentes
├─ packaging/
└─ tmp/                          # artefactos temporales ignorados
```

## 9. Estados del resultado

- `classified`: existe un único resultado y toda condición obligatoria tiene
  evidencia.
- `needs_input`: falta información que sí puede proporcionar el operador.
- `ambiguous`: dos ramas continúan siendo posibles.
- `conflict`: los datos se contradicen.
- `out_of_scope`: no pertenece al capítulo 72.
- `extraction_failed`: no se pudo leer el documento con confiabilidad.

La opción de revisión humana debe mostrar la evidencia y el punto exacto del
árbol donde se detuvo, no una caja para elegir arbitrariamente un código.
