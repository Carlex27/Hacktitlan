# Plan de desarrollo del backend y PostgreSQL

## Resumen

La importación XLSX comparte almacenamiento, trabajos y revisión con PDF.
Se conserva hoja/celda como evidencia y las cartas de resistencia permanecen
como documentación de apoyo, sin vinculación automática por especificación.
La química ambigua exige confirmación antes de normalizar; filas entre hojas
no se deduplican por suposición. El envío React ya utiliza la API. El siguiente
trabajo frontend es habilitar su toolchain y presentar las celdas y advertencias
del endpoint documentado.

La revisión de reglas del 8 de octubre de 2026 está documentada en
[`audit/CLASSIFICATION_SOURCE_REVIEW.md`](audit/CLASSIFICATION_SOURCE_REVIEW.md).
Antes de declarar cobertura completa deben resolverse las brechas de vigencia,
definiciones de aceros especiales, calificadores NICO y captura auditada de los
hechos faltantes. La disponibilidad de una ruta ejecutable no certifica la
clasificación jurídica de todos sus NICO.

El backend será una API FastAPI central conectada a PostgreSQL 18. Administrará
los PDF originales, el procesamiento en segundo plano, el historial, las
correcciones, la aprobación, la clasificación, las exportaciones y los respaldos.
El frontend y el segundo equipo accederán exclusivamente por la API mediante
Tailscale.

El orden detallado desde el estado actual hasta el cierre del backend está en
[`BACKEND_COMPLETION_PLAN.md`](BACKEND_COMPLETION_PLAN.md). Ese documento
incluye la explicación individual por candidato, el cierre de OCR pendiente y
los criterios finales de aceptación.

La primera entrega implementable es API + PostgreSQL + almacenamiento + trabajos
+ historial. OCR, reportes y modelos locales se conectan posteriormente sin
reemplazar la normalización determinista existente.

## Tecnología y restricciones

- Python 3.12 administrado mediante `pyproject.toml` y `uv.lock`.
- FastAPI y Pydantic 2 con versiones fijadas.
- SQLAlchemy 2.1 síncrono, Alembic y psycopg 3.
- PostgreSQL 18 instalado como servicio nativo en Windows 11 x64.
  Se mantendrá actualizado dentro de su versión estable conforme a la
  [política de versiones soportadas](https://www.postgresql.org/support/versioning/).
- Sin Docker, nube, Redis, Celery ni cuentas de usuario en la primera versión.
- API limitada a la interfaz Tailscale en operación; sin modo offline.
- Equipo mínimo: 8 GB de RAM y CPU sin GPU dedicada.

## Etapas

### 1. Fundamentos

- Configuración tipada para desarrollo, pruebas y servidor.
- Capas separadas de dominio, aplicación, repositorios, API e infraestructura.
- Errores estables, respuestas `data/meta/error`, logging estructurado,
  identificador de correlación y timestamps UTC.
- Conservación de `normalize_certificate` y todas sus pruebas actuales.

### 2. PostgreSQL y almacenamiento

- Migraciones para fabricantes, archivos, documentos, actas, coladas, productos,
  observaciones, composición, trabajos, extracciones, reglas, clasificaciones,
  decisiones, correcciones, aprobaciones, exportaciones y respaldos.
- Claves `bigint identity`, claves foráneas indexadas, restricciones de dominio e
  índices compuestos orientados a las consultas históricas.
- PDF en almacenamiento central configurable, publicados atómicamente después
  de calcular SHA-256.
- La ruta predeterminada es `C:\ProgramData\Hacktitlan\storage`; la escritura
  usa un temporal, verifica nuevamente el hash y publica mediante renombrado
  atómico.
- Mismo hash: operación idempotente. Mismo número de acta y distinto hash:
  revisión vinculada.
- Sin eliminación física; sólo archivado.

### 3. API y trabajos

- Salud, disponibilidad, carga/descarga, consultas paginadas, detalle histórico,
  evidencia, trabajos, correcciones, reclasificación, aprobación y rechazo.
- Carga `202 Accepted` con `document_id` y `job_id`.
- Cola PostgreSQL con `FOR UPDATE SKIP LOCKED`, heartbeat, recuperación de
  trabajos abandonados y máximo tres intentos.
- Estados técnicos independientes de `draft`, `needs_review`, `approved` y
  `rejected`.
- Persona y motivo obligatorios para corregir, aprobar o rechazar; equipo y fecha
  agregados por el backend.

### 4. Persistencia e historial

- Persistir actas, coladas, productos, composición y evidencia desde el contrato
  normalizado actual.
- Una corrección crea una nueva observación enlazada; nunca sobrescribe la
  anterior.
- Cada clasificación conserva entrada, reglas y pasos de decisión inmutables.
- Consultas mediante cursor por fecha, acta, fabricante, colada, producto,
  fracción, NICO y estado.
- Los periodos usan fecha del acta por defecto y admiten fecha de carga.

### 5. Clasificación, reportes y respaldo

La ejecución del Hito 7 está registrada en
[`audit/HITO_7_RESPALDO_VOLUMEN_RENDIMIENTO.md`](audit/HITO_7_RESPALDO_VOLUMEN_RENDIMIENTO.md).
El respaldo usa un snapshot PostgreSQL compartido entre conteos y `pg_dump`,
valida el ZIP antes de publicarlo y conserva un primario verificable si falla
la segunda copia. La restauración local exige base y carpetas vacías. El volumen
de cinco años ya se midió en desarrollo; la aceptación del servidor sigue pendiente.

- Reglas versionadas exclusivamente desde el PDF proporcionado.
- Resultados y reportes con la marca
  `DEMOSTRACIÓN — SIN VALIDEZ ADUANERA`.
- Reportes oficiales sólo con resultados aprobados; los demás son preliminares.
- XLSX por acta, colada o periodo conforme a `EXCEL_EXPORT_REQUIREMENTS.md`.
- Respaldo diario a las 02:00: 7 diarios, 4 semanales y 12 mensuales, con
  `pg_dump`, archivos, reglas, manifiesto y segunda copia configurable.
- Si Windows estaba apagado a las 02:00, el respaldo se ejecuta al iniciar.
- La exportación manual integral verifica hashes y `pg_restore --list`.
- Restauración sólo desde el servidor, nunca por endpoint remoto.

### 6. OCR y modelos posteriores

- PaddleOCR/PP-Structure implementarán la interfaz `DocumentReader`.
- Sin paquete OCR, el PDF se conserva y el trabajo termina en `needs_ocr`.
- Los modelos opcionales respetan `LOCAL_MODELS_REQUIREMENTS.md`.
- Se detectará CPU/GPU y se descargará únicamente el runtime compatible.
- Ningún modelo sustituye las reglas de normalización, validación o
  clasificación.

## Contratos públicos

- Respuestas uniformes `data`, `meta`, `error`.
- Cursores opacos basados en fecha e identificador.
- Desconocido se representa como `null`, nunca como cero o falso.
- Límite inicial configurable de 100 MB por PDF.
- Descargas por identificador administrado; no se aceptan rutas del cliente.
- La clasificación pertenece al producto, aunque la vista se agrupe por colada.

## Pruebas y aceptación

- Conservar las 24 pruebas existentes.
- Probar estados, restricciones, deduplicación, revisiones, cursores,
  aprobaciones, correcciones, worker y almacenamiento atómico.
- Integración real contra `hacktitlan_test`, incluyendo migraciones.
- Probar interrupción/reanudación de trabajos, correcciones inmutables y
  reproducción exacta de ejecuciones históricas.
- Restauración completa en una base vacía.
- Prueba de volumen de cinco años: 18,250 actas y hasta 273,750 coladas.
- Verificar paginación y filtros sobre ese volumen, que sólo resultados
  aprobados entren en reportes oficiales y que toda salida conserve la marca de
  demostración.
- Verificación en Windows 11 x64 con 8 GB de RAM.

## Supuestos cerrados

- Primer hito: API + PostgreSQL + almacenamiento + trabajos + historial.
- PostgreSQL será un servicio nativo, no Docker.
- Sin cuentas de usuario; Tailscale es la única barrera de acceso de esta etapa.
- Persona y motivo son obligatorios para aprobar, rechazar o corregir.
- Sin servidor no habrá consulta ni trabajo offline.
- Reportes agrupados por fecha del acta.
- Respaldo 7 diarios, 4 semanales y 12 mensuales con segunda copia configurable.
- Este archivo fue creado antes del primer cambio de implementación y conserva
  el plan aprobado completo.
