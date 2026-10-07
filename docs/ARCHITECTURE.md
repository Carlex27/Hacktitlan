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
| Base local | SQLite + migraciones Alembic | Cero servicio externo y empaquetado sencillo |
| Reportes | openpyxl + ReportLab | XLSX y PDF generados localmente |
| Pruebas | pytest + Hypothesis; Vitest/Playwright | Fronteras químicas, integración y UI |
| Empaquetado Python | PyInstaller | Sidecar autocontenido para Windows |
| Instalador | Tauri Bundler (MSI/NSIS) | Una sola instalación |

## 3. SQLite frente a PostgreSQL

Para una aplicación de una computadora, SQLite es técnicamente superior:

- se integra en un solo archivo;
- no instala ni administra un servicio;
- no abre puertos;
- simplifica respaldo, restauración e instalador;
- soporta holgadamente el volumen esperado de documentos y reglas.

PostgreSQL debe reservarse para una edición multiusuario en red local, con varios
equipos clasificando simultáneamente. El dominio y repositorios se diseñarán para
poder cambiar el adaptador sin alterar el motor de reglas.

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

## 5. Modelo de datos mínimo

- `documents`: archivo, hash, idioma, estado y fechas.
- `document_pages`: texto, imagen y estado OCR.
- `products`: rollo/lote/colada y relación con documento.
- `observations`: campo, valor original, valor normalizado, unidad, confianza,
  página y coordenadas.
- `chemical_compositions`: elemento y porcentaje por producto.
- `physical_properties`: ancho, espesor, diámetro, forma y enrollado.
- `mechanical_properties`: límite elástico y demás ensayos.
- `process_properties`: caliente/frío, decapado, revestimiento y tratamientos.
- `rule_sets`: versión, vigencia, fuente, hash y aprobación.
- `rules`: predicados y enlaces del grafo.
- `tariff_entries`: partida, subpartida, fracción, NICO y descripción.
- `classification_runs`: entrada, versión, resultado y estado.
- `decision_steps`: explicación de cada evaluación.
- `manual_overrides`: cambio, motivo, usuario y sello de tiempo.
- `exports`: formato y ubicación del reporte generado.

## 6. Contrato canónico de entrada

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

## 7. Estructura objetivo del repositorio

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
│  │  └─ infrastructure/         # SQLite, archivos y OCR
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

## 8. Estados del resultado

- `classified`: existe un único resultado y toda condición obligatoria tiene
  evidencia.
- `needs_input`: falta información que sí puede proporcionar el operador.
- `ambiguous`: dos ramas continúan siendo posibles.
- `conflict`: los datos se contradicen.
- `out_of_scope`: no pertenece al capítulo 72.
- `extraction_failed`: no se pudo leer el documento con confiabilidad.

La opción de revisión humana debe mostrar la evidencia y el punto exacto del
árbol donde se detuvo, no una caja para elegir arbitrariamente un código.
