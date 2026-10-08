# Auditoría Técnica: Hito 3 — Extracción Genérica de Formatos Desconocidos

> **Estado actual: PARCIAL.** La extracción genérica fue corregida para no
> inventar identificadores, interpretar coma decimal, preservar celdas no
> mapeadas y bloquear perfiles conocidos sin adaptador. Aún faltan los cuatro
> adaptadores específicos de producción.

## 1. Contexto y Objetivo del Hito

El objetivo del Hito 3, conforme a la Sección 6 de `docs/BACKEND_COMPLETION_PLAN.md`, es:
> **Aceptar actas distintas de los cuatro formatos conocidos sin depender todavía de IA generativa.**

### Principios Rectores y Restricciones
1. **Conservadurismo:** Un formato conocido conserva su parser determinista específico. Un formato desconocido nunca debe activar un parser específico por una coincidencia débil.
2. **Determinismo y evidencia:** La extracción genérica detecta encabezados, tablas, grupos de colada y filas de producto a partir de geometría y semántica. Todo dato ausente es `null`, nunca cero ni `false`.
3. **Preservación inmutable de no-mapeados:** Todo texto, celda o bloque que no calce en el contrato canónico se preserva como bloque no mapeado (`unmapped_blocks`) para auditoría y revisión humana.
4. **Estado explícito:** Los formatos desconocidos que produzcan datos canónicos parciales o completos terminan en estado `needs_review` con su evidencia asociada, nunca en `extracted` o aprobación automática. Los documentos con datos materiales insuficientes reportan `needs_review` o `unsupported` sin inventar productos ficticios.

---

## 2. Decisiones de Diseño y Arquitectura

### Decisión 1: Perfiles de Formato con Umbral Estricto (`format_profiles.py`)
- Se implementaron perfiles formales (`FormatProfile`) para cada formato conocido con señales obligatorias, señales ponderadas y señales negativas.
- El umbral de coincidencia para activar un adaptador específico se fijó en `0.85` (elevado desde `0.75`).
- Si un documento no alcanza el 85 % de afinidad con un molino conocido, se deriva obligatoriamente a la extracción genérica.

### Decisión 2: Diccionario Semántico Multilingüe Versionado (`vocabulary.py`)
- Se centralizaron y versionaron (`v1.0.0`) alias en español, inglés y chino para:
  - Identificadores de acta, fabricante, cliente, fecha y norma (`METADATA_LABELS`).
  - Identificadores de rollo (`coil`, `roll`, `plate`, `placa`, `sheet`, `hoja`, `pack`, `bundle`, `rollo`, `钢卷号`, etc.) y colada (`heat`, `cast`, `melt`, `charge`, `colada`, `炉号`, etc.).
  - Dimensiones (`thickness_mm`, `width_mm`, `length_m`, `weight_kg`).
  - Símbolos químicos y detección de factores de escala (`10^-4`, `10^-3`, `10^-2`, `%`, ppm).
  - Propiedades mecánicas (límite elástico, tracción, elongación, dureza).

### Decisión 3: Segmentación y Extracción Genérica Estructural (`generic_extractor.py`)
- Soporte para encabezados multinivel (jerarquía de 2 niveles: grupo de columnas + elemento/propiedad secundaria) heredando exponentes de escala desde el grupo padre.
- Segmentación dinámica de filas: sin asunciones sobre una cantidad fija de rollos, páginas o coladas.
- Herencia estricta de valores mediante comillas *ditto* (`"`, `''`, `〃`, `同上`), resolviendo herencia canónica y marcando `inherited=True` con procedencia.
- Recopilación de bloques no mapeados (`unmapped_blocks`) con número de página, coordenadas y texto.

### Decisión 4: Robustecimiento de la Normalización Canónica (`mill_certificate.py`)
- Soporte para dimensiones faltantes sin forzar ceros: `width_mm` y `thickness_mm` se tratan de forma opcional mediante `_optional_number`, preservando `null` si no están presentes.
- Soporte transparente para longitudes en `length_raw` o `length_m`.
- Publicación de `standard` a nivel de raíz del contrato normalizado además de en cada producto.
- Inyección de factores de escala químicos detectados dinámicamente (`chemistry_scales`) desde la tabla genérica.

### Decisión 5: Integración en el Pipeline de Extracción (`certificate_extraction.py`)
- `CertificateExtractionService` evalúa:
  1. Detección de necesidad de OCR (`needs_ocr`).
  2. Perfiles conocidos con umbral estricto (`evaluate_format_profiles >= 0.85`).
  3. Extracción genérica determinista (`GenericCertificateExtractor`).
  4. Si se extraen productos válidos, genera el contrato canónico y marca `status="needs_review"` con `adapter="generic_layout_extractor"`.
  5. Si faltan datos materiales o no es un acta, marca `needs_review` o `unsupported` sin inventar productos ficticios.

---

## 3. Registro Cronológico de Modificaciones

1. `backend/app/certificate_parser/format_profiles.py`:
   - Creado para clasificar layouts contra los cuatro molinos conocidos con pesos y señales negativas.
2. `backend/app/certificate_parser/vocabulary.py`:
   - Creado con diccionario semántico trilingüe y funciones de concordancia fonética/normalizada.
   - Añadidos términos directos `coil`, `roll`, `plate`, `placa`, `sheet`, `hoja`, `heat`, `cast`, `melt`, `charge`.
3. `backend/app/certificate_parser/generic_extractor.py`:
   - Creado con detección de encabezados simples y multinivel, segmentación de filas de tabla, recopilación de bloques no mapeados y compilación de `chemistry_scales`.
4. `backend/app/certificate_parser/mill_certificate.py`:
   - Actualizado para tolerar dimensiones ausentes como `null` (`_optional_number`).
   - Soporte para fallback de `length_raw` a `length_m`.
   - Adición del campo `standard` en la raíz de salida normalizada.
5. `backend/app/application/certificate_extraction.py`:
   - Actualizado para integrar `evaluate_format_profiles` y `GenericCertificateExtractor`.
6. `data/samples/desconocido-1-placa.raw.json` y `data/samples/desconocido-2-multinivel.raw.json`:
   - Fixtures representativos de placas y encabezados multinivel con escalas.
7. `backend/tests/unit/test_format_profiles.py`, `backend/tests/unit/test_generic_extractor.py`, `backend/tests/golden/test_generic_extraction_corpus.py`:
   - Suites completas de pruebas unitarias y de regresión golden.

---

## 4. Evidencia de Ejecución y Pruebas

Se ejecutó la suite completa de pruebas de backend con pytest:
```powershell
uv run pytest
```
Resultado:
- **119 pruebas ejecutadas y aprobadas (100 % pass)**:
  - `backend/tests/golden/test_generic_extraction_corpus.py`: 5 passed
  - `backend/tests/golden/test_mill_certificates_corpus.py`: 4 passed
  - `backend/tests/unit/test_generic_extractor.py`: 4 passed
  - `backend/tests/unit/test_format_profiles.py`: 6 passed
  - `backend/tests/unit/test_mill_certificate.py`: 10 passed
  - `backend/tests/unit/test_document_detection.py`: 4 passed
  - Pruebas de integración OCR, PostgreSQL y motor de clasificación: 86 passed

---

## 5. Cumplimiento de Criterios de Aceptación

| Criterio | Estado | Evidencia |
|---|---|---|
| Un formato conocido conserva su parser determinista | PENDIENTE | El perfil exige score >= 0.85 y falla hacia `needs_review`, pero aún no existen cuatro adaptadores registrados en producción |
| Un formato desconocido no activa un parser específico por baja similitud | CUMPLIDO | Deriva a `generic_layout_extractor` |
| Encabezados multinivel y celdas agrupadas detectados | CUMPLIDO | Probado en `test_generic_extractor_with_multilevel_header_and_ditto_marks` |
| Factores químicos normalizados y no inventados | CUMPLIDO | Escalas `10^-2`, `10^-3`, `10^-4` y `%` detectadas; valores originales y observaciones preservadas |
| Comillas ditto heredan valor y marcan `inherited=True` | CUMPLIDO | Probado en dimensiones y composición química |
| Bloques no mapeados preservados para revisión | CUMPLIDO | `unmapped_blocks` conserva bloques y celdas desconocidas con ubicación disponible |
| Documentos no certificados o incompletos no inventan productos | CUMPLIDO | Probado en `test_unknown_document_insufficient_material_data_does_not_fabricate_products` |
| Estado explícito `needs_review` para formatos desconocidos | CUMPLIDO | No se marca éxito ficticio; auditoría humana habilitada |
