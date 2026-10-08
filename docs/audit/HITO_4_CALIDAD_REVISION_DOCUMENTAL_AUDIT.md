# Auditoría de Código — Hito 4: Calidad y Revisión Documental

**Fecha de ejecución:** 8 de octubre de 2026  
**Rama:** `backend`  
**Objetivo del hito:** Convertir la extracción en un proceso medible, determinista y corregible antes de clasificar, conforme a la Sección 7 de `docs/BACKEND_COMPLETION_PLAN.md` ("Calidad y revisión documental"). Garantizar que ningún producto llegue al motor de clasificación sin contrato válido, que todo dato dudoso conserve su valor original, motivo y región de evidencia, y habilitar una cola de revisión y reprocesamiento multi-etapa independiente.

---

## 1. Resumen Ejecutivo

En este hito se diseñó e implementó la arquitectura integral de aseguramiento de calidad documental para el procesamiento de actas de molino (MTR). La extracción de datos ahora cuenta con una capa formal de evaluación previa a cualquier toma de decisión arancelaria.

Se construyó un motor de calidad puro en el dominio (`backend/app/domain/document_quality.py`) que detecta anomalías matemáticas, físicas y de alcance en los documentos, evalúa la suficiencia de datos según la familia del producto (`flat_rolled_coil`, `flat_rolled_plate`, etc.), califica la confianza de extracción por campo (con umbral mínimo de `0.70`), y separa estrictamente las incidencias en cuatro categorías canónicas: `missing`, `low_confidence`, `contradiction` y `anomaly`.

Se integró una compuerta estricta en el servicio de clasificación (`ClassificationService`), impidiendo que productos con datos inconsistentes o dudosos generen clasificaciones adivinadas o candidatos artificiales. Asimismo, se incorporó una cola de revisión documental independiente en la API pública (`GET /api/v1/document-reviews`), un endpoint de diagnóstico detallado por acta (`GET /api/v1/certificates/{id}/quality-report`), y soporte de reprocesamiento multi-etapa (`POST /api/v1/certificates/{id}/reprocess`) desde extracción, normalización o clasificación preservando el historial inmutable.

---

## 2. Decisiones de Diseño y Arquitectura

### 2.1. Modelo de Dominio de Calidad Documental (`backend/app/domain/document_quality.py`)
- **Independencia del dominio:** El validador `validate_document_quality` es una función pura, libre de dependencias de base de datos o frameworks web, lo que permite su ejecución tanto en segundo plano como sincrónicamente en la API.
- **Tipado exhaustivo:**
  - `QualityCategory`: `missing` (campo obligatorio ausente), `low_confidence` (confianza de extracción menor a 0.70), `contradiction` (inconsistencia física o normativa), `anomaly` (desalineación de alcance o integridad).
  - `QualitySeverity`: `blocking` (impide clasificación automática; fuerza `needs_review`) y `warning` (aviso operativo sin bloqueo estricto).
  - `ProductFamily`: `flat_rolled_coil` (bobinas/rollos), `flat_rolled_plate` (placas/hojas), `flat_rolled_general` y `unknown`.
  - `QualityIssue`: Data transfer object inmutable que preserva código, ámbito (`certificate`, `heat`, `product`, `chemistry`), campo, mensaje explicativo, valor original (`raw_value`), valor normalizado (`normalized_value`), confianza, página y bounding box (`bbox`).
  - `DocumentQualityReport`: Reporte integral con estado (`clean` o `needs_review`), puntuación de calidad `quality_score` de 0.0 a 1.0, conteo de bloqueos/advertencias, resumen de procedencia y lista de incidencias.

### 2.2. Detección de Contradicciones Físicas y de Dominio
1. **Dimensiones y pesos no físicos:**
   - Todo espesor (`thickness_mm`), ancho (`width_mm`), longitud (`length_m`) o peso (`weight_kg`) menor o igual a cero (`<= 0`) genera inmediatamente una incidencia de categoría `contradiction` con severidad `blocking` (`impossible_dimension`).
2. **Química imposible:**
   - La suma de porcentajes químicos no puede superar el 100.0 % en ningún alcance (colada o producto). Si $\sum \text{pct} > 100.0\,\%$, se emite `chemical_sum_exceeds_100` (`contradiction`, `blocking`).
   - Ningún elemento individual puede tener un porcentaje menor a 0 % o mayor a 100 %. Si se detecta, se emite `chemical_percentage_out_of_range` (`contradiction`, `blocking`).
3. **Unidades incoherentes:**
   - Las dimensiones de laminados deben estar expresadas en milímetros (`mm`). Unidades incompatibles (como pulgadas o metros sin normalizar) arrojan `incoherent_unit` (`contradiction`, `blocking`).
   - Las composiciones químicas deben ser fraccionarias o porcentuales (`%`, `wt%`, `ppm`). Unidades de masa directa (p. ej. `kg`) en campos porcentuales arrojan `incoherent_unit`.
4. **Conflictos en coladas duplicadas:**
   - Si una misma colada (`heat_no`) aparece duplicada en el acta con normas técnicas (`standard`) o grados de acero (`grade`) contradictorios, se emite `duplicate_heat_conflict` (`contradiction`, `blocking`).
5. **Integridad de alcance y orfandad:**
   - Si un producto referencia un identificador de colada que no existe en el acta, se marca `orphaned_product` (`contradiction`, `blocking`).
   - Si un producto no tiene análisis químico propio ni tampoco heredado de su colada, se marca `missing_required_chemistry` (`missing`, `blocking`).

### 2.3. Trazabilidad de Confianza y Procedencia
- **Umbral de corte:** Se fijó `CONFIDENCE_THRESHOLD_MIN = 0.70`.
- Campos críticos con confianza menor a 0.70 (espesor, ancho, química) generan incidencias bloqueantes de categoría `low_confidence`. Campos no críticos generan advertencias (`warning`).
- La procedencia se clasifica en 5 fuentes canónicas:
  - `digital_text`: Extracción digital directa del PDF (confianza $\ge 0.90$).
  - `ocr_text`: Texto obtenido mediante inferencia OCR.
  - `inherited`: Datos propagados mediante jerarquía o comillas ditto.
  - `manual_capture`: Datos aportados o corregidos por un analista.
  - `unknown`: Procedencia no atribuible con certeza.

### 2.4. Compuerta de Calidad en el Motor de Clasificación
- En `ClassificationService.classify_certificate`, se ejecuta la evaluación de calidad antes de invocar las reglas de la LIGIE.
- Si existen incidencias bloqueantes asociadas al producto o al acta (`has_blocking`):
  - El resultado se fija irrevocablemente a `outcome = "needs_review"`.
  - La fracción arancelaria (`fraction`), NICO (`nico`) y descripción se establecen en `None`.
  - La lista de candidatos se vacía (`candidates = []`, `valid_candidate_count = 0`).
  - Las incidencias completas se adjuntan en `details_json["quality_issues"]`, junto con el `quality_score` y el `document_quality_status`.
  - **Criterio de salida cumplido:** Ningún producto avanza al motor arancelario con datos inconsistentes ni recibe códigos adivinados.

### 2.5. Corrección Inmutable y Sincronización de Entidades (`ReviewService`)
- Al aplicar una corrección vía `ReviewService.correct_observation` o agregar un dato vía `add_manual_observation`:
  1. La observación anterior se marca como no vigente (`is_current = False`).
  2. La nueva observación se crea con `is_current = True`, `confidence = 1.0`, `supersedes_id = previous.id`.
  3. Se registra el evento de auditoría en la tabla `corrections` (persona, motivo, estación, timestamp).
  4. Mediante el método `_sync_entity_field`, se sincroniza la columna correspondiente en la tabla `Product` (`thickness_mm`, `width_mm`, `form`, `coiled`, etc.) o `ChemicalComposition`.
  5. En `DocumentQualityService.evaluate_certificate`, las observaciones vigentes tienen prelación dinámica sobre los registros base, garantizando que una corrección manual limpie de inmediato el reporte de calidad.

### 2.6. Reprocesamiento Multi-Etapa y Cola de Revisión
- Se implementó `DocumentQualityService.reprocess_certificate`:
  - `extraction`: Encola un nuevo trabajo de extracción (`JobKind.EXTRACT_DOCUMENT`) a partir del archivo original almacenado en disco (`StoredFile`), sin requerir volver a subir el PDF.
  - `normalization`: Re-evalúa inmediatamente la calidad documental y el contrato vigente. Si todas las incidencias fueron resueltas, actualiza el estado del acta y del documento a `succeeded` / `draft`; de lo contrario, los mantiene en `needs_review`.
  - `classification`: Encola un nuevo trabajo de reclasificación (`JobKind.RECLASSIFY`) generando una nueva ejecución vinculada (`ClassificationRun`) con instantánea inmutable.
  - Se exige de forma obligatoria `person_name` y `reason` en la solicitud (`ReprocessRequest`).

---

## 3. Registro Cronológico de Modificaciones

1. **`backend/app/domain/document_quality.py`** *(Nuevo)*:
   - Definición de enums `QualityCategory`, `QualitySeverity`, `ProductFamily`.
   - Data classes `QualityIssue` y `DocumentQualityReport`.
   - Funciones `detect_product_family` y `validate_document_quality`.
2. **`backend/app/application/document_quality_service.py`** *(Nuevo)*:
   - Clase `DocumentQualityService` con métodos `evaluate_certificate`, `get_review_queue` y `reprocess_certificate`.
   - Lógica de overlay de observaciones vigentes para evaluación en caliente.
3. **`backend/app/application/classification_service.py`** *(Modificado)*:
   - Integración de `DocumentQualityService` en `classify_certificate`.
   - Compuerta estricta que bloquea candidatos y código cuando existen incidencias no resueltas.
4. **`backend/app/application/review_service.py`** *(Modificado)*:
   - Inclusión de `_sync_entity_field` para sincronizar `Product` y `ChemicalComposition` al corregir o agregar observaciones.
5. **`backend/app/api/schemas.py`** *(Modificado)*:
   - Modelos Pydantic: `QualityIssueItem`, `DocumentQualityReportRead`, `DocumentReviewSummaryIssue`, `DocumentReviewQueueItem`, `ReprocessRequest`, `ReprocessRead`.
   - Envolventes de respuesta: `DocumentQualityReportEnvelope`, `DocumentReviewQueueEnvelope`, `ReprocessEnvelope`.
6. **`backend/app/api/app.py`** *(Modificado)*:
   - Registro de los endpoints públicos:
     - `GET /api/v1/document-reviews`
     - `GET /api/v1/certificates/{certificate_id}/quality-report`
     - `POST /api/v1/certificates/{certificate_id}/reprocess`
7. **`backend/tests/unit/test_document_quality.py`** *(Nuevo)*:
   - Suite de 9 pruebas unitarias cubriendo familias, campos faltantes, contradicciones físicas, duplicados, orfandad y umbrales de confianza.
8. **`backend/tests/integration/test_document_quality_and_review.py`** *(Nuevo)*:
   - Suite de 4 pruebas de integración sobre PostgreSQL 18 cubriendo endpoints de calidad, cola de revisión, etapas de reprocesamiento y flujo completo de compuerta y corrección.
9. **`docs/BACKEND_COMPLETION_PLAN.md`** y **`docs/BACKEND_IMPLEMENTATION_STATUS.md`** *(Modificados)*:
   - Actualización de estado y documentación del Hito 4.

---

## 4. Evidencia de Ejecución y Pruebas

### 4.1. Pruebas Unitarias del Dominio de Calidad
```powershell
uv run pytest backend/tests/unit/test_document_quality.py
```
**Resultado:**
- 9 passed en 0.05 s:
  - `test_detect_product_family`: Detección precisa de bobina vs plancha vs general.
  - `test_validate_document_quality_clean`: Acta perfecta produce score 1.0, estado `clean` y 0 incidencias.
  - `test_mandatory_fields_missing`: Ausencia de número de acta, espesor o ancho detectada como bloqueante.
  - `test_impossible_dimensions`: Espesor $\le 0$, ancho $\le 0$ y peso $\le 0$ marcados como contradicciones físicas bloqueantes.
  - `test_chemistry_out_of_range_and_impossible_sum`: Suma $> 100\,\%$ y porcentajes $> 100\,\%$ detectados como contradicciones bloqueantes.
  - `test_duplicate_heat_conflict`: Coladas duplicadas con normas distintas detectadas como contradicciones bloqueantes.
  - `test_orphaned_product`: Producto con `heat_id` inexistente marcado como anomalía bloqueante.
  - `test_incoherent_units`: Unidades no métricas o incongruentes marcadas como contradicciones bloqueantes.
  - `test_low_confidence_separation`: Confianza menor a 0.70 separada correctamente como `low_confidence`.

### 4.2. Pruebas de Integración de API y Flujo de Calidad
```powershell
uv run pytest backend/tests/integration/test_document_quality_and_review.py
```
**Resultado:**
- 4 passed en 2.41 s:
  - `test_quality_report_endpoint_clean_and_not_found`: Endpoint `/quality-report` entrega esquema envelope completo y responde 404 en actas inexistentes.
  - `test_document_reviews_queue`: Endpoint `/document-reviews` lista documentos con incidencias y omite actas limpias aprobadas.
  - `test_reprocess_stages`: Verificación de reprocesamiento en etapas `normalization`, `extraction` y `classification`, junto con validación de esquemas erróneos (422).
  - `test_quality_gating_and_manual_correction_flow`: Flujo integral validado sobre PostgreSQL:
    1. Acta con espesor de baja confianza (0.45) produce reporte `needs_review`.
    2. La clasificación inicial bloquea candidatos (`candidates=[]`, `outcome="needs_review"`, `fraction=None`).
    3. El usuario corrige la observación mediante la API (`POST /observations/{id}/corrections`).
    4. La observación previa se reemplaza y la nueva se audita con confianza 1.0.
    5. Se invoca reprocesamiento desde normalización (`POST /reprocess`), actualizando el reporte de calidad a `clean`.
    6. La reclasificación subsiguiente procesa las reglas con éxito y genera las opciones arancelarias correspondientes.

### 4.3. Suite Completa del Repositorio
```powershell
uv run pytest
```
**Resultado:**
- **168 pruebas aprobadas (100.0 % pass)** en 7.65 s.
- **Validación OpenAPI:** 29 rutas registradas y verificadas contra el contrato FastAPI.

---

## 5. Cumplimiento de Criterios de Aceptación

| Requisito del Plan (Sección 7) | Estado | Evidencia de Implementación y Auditoría |
| :--- | :---: | :--- |
| **Definir campos obligatorios por familia de producto** | CUMPLIDO | `detect_product_family()` y reglas de obligatoriedad en `validate_document_quality()` para bobinas, placas y chapas. |
| **Calcular confianza por campo y procedencia** | CUMPLIDO | Conteo y clasificación de fuentes en `provenance_summary` (`digital_text`, `ocr_text`, `inherited`, `manual_capture`); umbral mínimo 0.70. |
| **Separar baja confianza, dato ausente y contradicción** | CUMPLIDO | Enum `QualityCategory` con categorías formalmente desacopladas (`missing`, `low_confidence`, `contradiction`, `anomaly`). |
| **Detectar totales imposibles, porcentajes fuera de rango y unidades incoherentes** | CUMPLIDO | Sumas $> 100\,\%$, porcentajes $<0$ o $>100$, dimensiones $\le 0$ y unidades ajenas a `mm`/`%` emiten incidencias `blocking`. |
| **Detectar coladas duplicadas dentro de una revisión** | CUMPLIDO | Detección de `duplicate_heat_conflict` cuando existen normas o grados contradictorios bajo el mismo número de colada. |
| **Validar que productos y composiciones tengan alcance correcto** | CUMPLIDO | Detección de `orphaned_product` (colada inexistente) y `missing_required_chemistry` (ausencia de análisis químico propio o de colada). |
| **Incorporar una cola de revisión documental independiente** | CUMPLIDO | Endpoint `GET /api/v1/document-reviews` con paginación, filtros de estado y resumen de anomalías. |
| **Registrar correcciones como nuevas observaciones** | CUMPLIDO | Inmutabilidad garantizada: `is_current=False` para la anterior, nueva observación con `is_current=True`, `confidence=1.0` y registro en `corrections`. |
| **Permitir reprocesar desde extracción, normalización o clasificación** | CUMPLIDO | Endpoint `POST /api/v1/certificates/{id}/reprocess` con selector `from_stage` (`extraction`, `normalization`, `classification`) y auditoría obligatoria. |
| **Criterio de salida: Ningún producto llega al motor sin contrato válido** | CUMPLIDO | Gating en `ClassificationService`: bloqueo de fracciones/candidatos cuando `has_blocking=True`, preservando datos originales, motivos y regiones de evidencia. |
