# Auditoría de Código — Hito 5: Cobertura Completa de Reglas Aprobadas

**Fecha de ejecución:** 8 de octubre de 2026  
**Rama:** `backend`  
**Objetivo del hito:** Implementar la cobertura determinista y exhaustiva para todas las partidas de laminados planos del Capítulo 72 según la Sección 8 de `docs/BACKEND_COMPLETION_PLAN.md` ("Cobertura final del motor de clasificación"), garantizando cero ramas omitidas silenciosamente, modelado de hechos faltantes y anomalías oficiales, inmutabilidad de conjuntos de reglas aprobadas, y reproducibilidad histórica estricta.

---

## 1. Resumen Ejecutivo

En este hito se construyó una matriz formal para cada partida, fracción y NICO del catálogo versionado (614 elementos). La matriz distingue cobertura ejecutable, ramas bloqueadas, anomalías, ramas aún no implementadas y elementos fuera de alcance.

Se expandió el motor de clasificación `Chapter72ClassificationEngine` para cubrir las 9 partidas de laminados planos (`7208`, `7209`, `7210`, `7211`, `7212`, `7219`, `7220`, `7225`, `7226`), respetando las notas de capítulo de la LIGIE (Nota 1(e) para acero inoxidable, Nota 1(f) para demás aceros aleados, Nota 1(k) para productos chapeados).

Asimismo, se implementó el aislamiento estricto ante anomalías de la fuente oficial (fracción `7219.35.02`), el soporte de candidatos y factores explicativos para las nuevas partidas, la inmutabilidad de reglas aprobadas y retiradas, y la reproducibilidad determinista a partir de instantáneas históricas.

---

## 2. Matriz de Cobertura del Capítulo 72

El archivo `backend/app/classification_engine/coverage.py` formaliza la matriz exhaustiva de cobertura. Todo el catálogo versionado (`614` registros: 29 partidas, 176 fracciones, 409 NICOs) se encuentra tipado y evaluado:

| Estado de Rama (`BranchStatus`) | Total | Descripción y Alcance |
| :--- | :---: | :--- |
| `implemented` | **285** | Ramas respaldadas por una fracción alcanzable desde el motor. |
| `blocked_by_missing_fact` | **17** | Fracciones y NICOs descendientes que requieren hechos externos no determinables exclusivamente a partir del certificado de molino estándar (pérdidas magnéticas W/kg a 50/60 Hz, destino industrial específico como cuerpos de envases de hojalata, o ensayos de embutición profunda para paneles automotrices). |
| `ambiguous_source` | **2** | Código de fracción y NICO `7219.35.02` con anomalía documentada en la fuente oficial proporcionada (`SIN VIGENCIA`). |
| `not_implemented` | **6** | Fracciones o NICOs sin ruta ejecutable; incluyen `7208.90.99`, `7209.90.99` y `7210.41.99`. |
| `out_of_scope` | **304** | Partidas del Capítulo 72 correspondientes a productos no planos (desperdicios `7204`, lingotes `7206-7207`, alambrón `7213`, barras `7214-7215`, perfiles `7216`, alambre `7217`, barras de inoxidable `7221-7223`, barras de demás aleados `7227-7229`). |
| **Total General** | **614** | **100% está mapeado; 6 elementos permanecen explícitamente pendientes de implementación.** |

### Partidas de Laminados Planos en Alcance (9 Partidas):
1. **7208**: Productos laminados planos de hierro o acero sin alear, de anchura $\ge 600\text{ mm}$, laminados en caliente, sin chapar ni revestir.
2. **7209**: Productos laminados planos de hierro o acero sin alear, de anchura $\ge 600\text{ mm}$, laminados en frío, sin chapar ni revestir.
3. **7210**: Productos laminados planos de hierro o acero sin alear, de anchura $\ge 600\text{ mm}$, chapados o revestidos (estaño, plomo, cinc electrolítico, cinc por inmersión en caliente, óxidos de cromo/TFS, aluminio-cinc, aluminio, pintura/plástico).
4. **7211**: Productos laminados planos de hierro o acero sin alear, de anchura $< 600\text{ mm}$, sin chapar ni revestir (laminados en las 4 caras `7211.13`, caliente espesor $\ge 4.75\text{ mm}$ `7211.14`, caliente espesor $< 4.75\text{ mm}$ `7211.19`, frío carbono $< 0.25\%$ `7211.23`, frío carbono $\ge 0.25\%$ `7211.29`).
5. **7212**: Productos laminados planos de hierro o acero sin alear, de anchura $< 600\text{ mm}$, chapados o revestidos (estañados `7212.10`, cincados electrolíticamente `7212.20`, cincados térmicamente `7212.30`, pintados/plastificados `7212.40`, demás revestidos `7212.50`, chapeados `7212.60`).
6. **7219**: Productos laminados planos de acero inoxidable, de anchura $\ge 600\text{ mm}$ (caliente enrollado y plano en cortes $>10\text{ mm}$, $\ge 4.75\text{ mm}$, $\ge 3\text{ mm}$, $<3\text{ mm}$; frío $\ge 4.75\text{ mm}$, $\ge 3\text{ mm}$, $>1\text{ mm}$, $\le 1\text{ mm}$).
7. **7220**: Productos laminados planos de acero inoxidable, de anchura $< 600\text{ mm}$ (caliente $\ge 4.75\text{ mm}$ `7220.11`, caliente $< 4.75\text{ mm}$ `7220.12`, frío `7220.20`, los demás `7220.90`).
8. **7225**: Productos laminados planos de los demás aceros aleados, de anchura $\ge 600\text{ mm}$ (acero magnético al silicio `7225.11` grano orientado y `7225.19` demás, caliente enrollado `7225.30`, caliente sin enrollar `7225.40`, frío `7225.50`, revestidos de cinc `7225.91`/`7225.92`, demás revestidos `7225.99`).
9. **7226**: Productos laminados planos de los demás aceros aleados, de anchura $< 600\text{ mm}$ (magnético al silicio de grano orientado `7226.11`, demás magnético `7226.19`, acero rápido `7226.20`, caliente `7226.91`, frío `7226.92`, los demás `7226.99`).

---

## 3. Decisiones de Diseño y Tratamiento de Casos Críticos

### 3.1. Detección y No Resolución Arbitraria de la Anomalía Oficial en `7219.35.02`
- **Problema encontrado:** En el catálogo oficial proporcionado (`data/ligie/chapter-72/source-provided/catalog.json`, derivado del PDF oficial marcado `SIN VIGENCIA`), la fracción `7219.35.02` aparece duplicada en las páginas 38 (bajo la subpartida `7219.34` de espesor $\ge 0.5\text{ mm}$ pero $\le 1\text{ mm}$) y 39 (bajo la subpartida `7219.35` de espesor $< 0.5\text{ mm}$), con descripciones y NICOs contradictorios.
- **Principio aplicado:** Cumpliendo estrictamente el mandato de la Sección 8 ("Códigos duplicados en la fuente no se resuelven por orden"), el motor no selecciona la primera opción ni infiere arbitrariamente.
- **Implementación:** Al evaluar acero inoxidable en frío de ancho ancho con espesor $\le 1\text{ mm}$, el motor genera explícitamente:
  - `missing_fields`: `{"ambiguous_source_code_7219_35_02"}`.
  - Paso de decisión: `chapter72.stainless.source_anomaly_7219_35_02` con resultado `StepOutcome.AMBIGUOUS`.
  - Explicación: *"Anomalía en la fuente original (PDF LIGIE SIN VIGENCIA páginas 38-39): la fracción 7219.35.02 aparece duplicada con distintas descripciones."*
  - Estado final: `needs_review`.

### 3.2. Preservación Estricta de Hechos Nulos
- Las propiedades físicas, químicas o de acabado ausentes **nunca se convierten en `0` ni en `false`**.
- Un campo no informado permanece `None` y genera un resultado `StepOutcome.MISSING` o `StepOutcome.UNKNOWN`, marcando el campo exacto en `missing_fields` y conservando los candidatos como condicionales (`conditional`).

### 3.3. Nuevos Atributos en `ProductFacts` y Persistencia
Se incorporaron los campos requeridos por los NICO de acabado, temple y uso sin romper contratos previos:
- `grain_oriented: bool | None`: Grano orientado (crucial para subpartidas magnéticas `7225.11` y `7226.11`).
- `magnetic_silicon: bool | None`: Acero magnético al silicio / chapa magnética.
- `stainless_series: str | None`: Serie de acero inoxidable (`"300"`, `"400"`, `"200"`), inferible por química o declarado explícitamente.
- `rolled_four_faces: bool | None`: Laminado en las cuatro caras (desempate para `7211.13`).
- `clad: bool | None`: Chapeado mecánico o térmico (desempate para `7212.60`).
- `temper: str | None`: Temple o dureza comercial.

Todos estos atributos fueron incorporados en `ClassificationService._facts()` (extracción desde `properties_json` u `Observation`), `ClassificationService._snapshot()` (serialización histórica inmutable) y reconstrucción en pruebas.

### 3.4. Reglas de Candidatos y Exclusión Justificada
- Las opciones que contradicen propiedades conocidas del producto se descartan formalmente y se registran en `discarded_candidates` con `reason_code="known_facts_conflict"`.
- Los candidatos sólo se devuelven si existen en el catálogo versionado y pasan la validación de integridad (`catalog.validate_result`).
- Nunca se "rellena" artificialmente la lista a 3 candidatos por similitud cuando la legislación sólo admite 1 o 2 opciones válidas; en tal caso, el resultado permanece justamente en `needs_review` exigiendo revisión del especialista.

### 3.5. Inmutabilidad y Versionado de Conjuntos de Reglas (`versioning.py`)
- `validate_rule_set_immutability(status, field_changed)` está conectada a un evento ORM y la migración `0006_rule_set_immutability` instala además un trigger PostgreSQL. Las escrituras desde la aplicación y las escrituras SQL directas quedan protegidas.
- Se implementó `compare_rule_sets(current_manifest, target_manifest)` para auditar diferencias (reglas añadidas, eliminadas, modificadas y cambio de hash de catálogo) antes de cualquier reclasificación histórica.
- Se aseguró en `ClassificationService._rule_set()` que un conjunto con estado `retired` no pueda iniciar nuevas clasificaciones, arrojando el error `rule_set_retired`.

---

## 4. Pruebas de Frontera y Umbrales Exactos

Se creó la suite integral de pruebas unitarias `backend/tests/unit/test_chapter72_coverage.py` que verifica el comportamiento matemático estricto en la frontera de cada parámetro:

1. **Umbrales químicos de aleación y acero inoxidable (Nota 1(e) y 1(f)):**
   - Cromo en `10.4999%` vs `10.5000%` vs `10.5001%`: A `10.4999%` no es inoxidable; a `10.5000%` con $C \le 1.2\%$ entra a partida `7219` (inoxidable).
   - Carbono en `1.2000%` vs `1.2001%`: Con $Cr = 10.5\%$, a `1.2000%` es inoxidable; a `1.2001%` excede el límite y pasa a `7225` (demás aceros aleados).
   - Boro en `0.00079%` vs `0.00080%` vs `0.00081%`: Inclusivo en $\ge 0.0008\%$.
   - Titanio en `0.0499%` vs `0.0500%`: Inclusivo en $\ge 0.05\%$.

2. **Umbrales dimensionales:**
   - Ancho en `599.9 mm` (partida estrecha `7211`/`7212`/`7220`/`7226`) vs `600.0 mm` y `600.1 mm` (partida ancha `7208`/`7209`/`7210`/`7219`/`7225`).
   - Espesores en `0.349` vs `0.350` vs `0.351 mm` (galvanizados `7210.49` y estrechos `7211.23`).
   - Espesores en `0.499` vs `0.500` vs `0.501 mm` (hojalata `7210.11` vs `7210.12`).
   - Espesores en `0.999` vs `1.000` vs `1.001 mm` (`7209.17` vs `7209.16`).
   - Espesores en `2.999` vs `3.000` vs `3.001 mm` (`7209.16` vs `7209.15`).
   - Espesores en `4.749` vs `4.750` vs `4.751 mm` (`7211.19` vs `7211.14` y `7219.13` vs `7219.12`).
   - Espesores en `9.999` vs `10.000` vs `10.001 mm` (`7208.25` NICO `99` vs `01` y `7219.12` vs `7219.11`).

3. **Umbrales mecánicos:**
   - Límite de fluencia en `354.9 MPa` (NICO `99`) vs `355.0 MPa` (NICO `01` de alta resistencia) vs `355.1 MPa` (NICO `01`).

4. **Reproducibilidad histórica:**
   - `POST /api/v1/certificates/{id}/reclassify` acepta `source_run_id`, reconstruye hechos y evidencia desde `input_snapshot_json`, reutiliza el conjunto de reglas original y enlaza la nueva ejecución mediante `parent_run_id`.
   - Cada snapshot registra `engine_sha256`. Si el motor exacto ya no está disponible, la operación devuelve `historical_engine_unavailable` en vez de producir un resultado silenciosamente distinto.

---

## 5. Resultados de Validación y Verificación

La suite completa de pruebas del backend se ejecutó exitosamente:

```bash
uv run pytest
======================= 199 passed, 1 warning in 8.74s ========================
```

El total se toma de la ejecución completa, sin mantener un desglose manual que pueda quedar desactualizado.

**Total: 199 pruebas unitarias e integrales aprobadas, 0 fallos.**

---

## 6. Cumplimiento de Reglas del Repositorio (`AGENTS.md`)

1. **Separación de responsabilidades:** La lógica de clasificación física y química, validación arancelaria y detección de anomalías vive exclusivamente en el backend (`backend/app/classification_engine/`).
2. **Preservación de evidencia:** No se infieren valores ausentes; permanecen como `None` y generan requerimientos explícitos de revisión documental.
3. **Modelado explícito de estados:** Se modelan formalmente `implemented`, `blocked_by_missing_fact`, `ambiguous_source` y `out_of_scope`.
4. **Listas dinámicas:** Los factores son dinámicos y el flujo conserva hasta tres candidatos conforme al contrato de revisión.
5. **Aduanal Safety Notice:** Se preserva en toda salida y reporte la leyenda obligatoria `DEMOSTRACIÓN — SIN VALIDEZ ADUANERA`.
