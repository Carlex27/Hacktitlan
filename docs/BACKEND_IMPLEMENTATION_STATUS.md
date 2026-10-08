# Estado de implementación del backend

## Implementado

- Runtime Python 3.12 y dependencias fijadas mediante `uv.lock`.
- Configuración tipada, errores estables, respuestas `data/meta/error`, logs
  JSON, correlación y timestamps con zona horaria.
- Esquema PostgreSQL de 21 tablas con `bigint identity`, integridad, índices y
  migración Alembic inicial; incluye el conjunto de reglas proporcionado en
  estado `draft` y con su hash de fuente.
- Almacenamiento central atómico y direccionado por SHA-256, deduplicación y
  revisiones de acta.
- API v1 de salud, carga/descarga, actas, coladas, rollos, evidencia, archivo,
  trabajos, cancelación, correcciones, aprobación/rechazo y exportación XLSX.
- Cola PostgreSQL con `SKIP LOCKED`, heartbeat, recuperación y tres intentos.
- Persistencia del contrato normalizado actual sin cambiar los cuatro parsers.
- Correcciones inmutables, eventos de aprobación y separación entre estado
  técnico y estado de aprobación.
- XLSX oficial/preliminar con ocho hojas, tablas, vínculos, formato, marca de
  demostración, validación y descarga administrada.
- Respaldo completo verificado, segunda copia, retención 7/4/12, ejecución a las
  02:00 con recuperación de tarea perdida y restauración sólo local.
- Scripts de arranque, preparación PostgreSQL y firewall Tailscale.
- Motor determinista conservador para laminados planos: familia metalúrgica,
  ramas iniciales 7208/7209/7210/7225, validación contra catálogo, candidatos,
  faltantes y pasos reproducibles.
- Reclasificación en segundo plano, ejecuciones enlazadas, instantáneas
  inmutables, captura manual de datos faltantes y bloqueo de aprobación cuando
  falta fracción o NICO.
- Generación y persistencia de hasta tres candidatos completos y validados
  contra catálogo. La selección exige exactamente tres opciones, persona y
  motivo; conserva historial inmutable y queda separada de la aprobación.
- Expansión de NICO para fracciones deterministas, con ranking estable y filtros
  de compatibilidad para 7208 y 7225. Incluye fronteras de boro, espesor,
  enrollado, decapado, resistencia, tubería y porcelanizado.
- API para consultar candidatos e historial mediante la ejecución y registrar
  la selección en `/api/v1/classification-results/{result_id}/select`.
- Enlaces `evidence_links` entre cada paso y sus observaciones exactas. La API
  `/api/v1/evidence/{evidence_link_id}` entrega página, coordenadas y URL
  administrada del PDF; sin coordenadas declara una vista de página completa.
- Persistencia de página, región, texto fuente y confianza cuando el extractor
  proporciona geometría para propiedades y composición química.
- Flujo integral validado sobre PostgreSQL 18: carga `202`, almacenamiento,
  trabajo en cola, ejecución, persistencia de actas/coladas/productos/química,
  consulta por API y deduplicación por SHA-256.
- El worker sincroniza el estado técnico del documento al iniciar, reintentar o
  fallar. Los formatos incompletos terminan en `needs_review` y los PDF sin
  texto utilizable terminan en `needs_ocr` sin crear productos ficticios.
- Pruebas reales separadas en `hacktitlan_test` para conexión, versión,
  migraciones, disponibilidad de API y flujo completo de procesamiento.
- Integración opcional de PP-StructureV3 mediante `DocumentReader`, sin cargar
  PaddleOCR durante el arranque. Conserva texto, confianza, coordenadas y tablas.
- Diagnóstico de RAM, arquitectura, GPU NVIDIA, runtime Paddle y dispositivo
  activo mediante `/api/v1/ocr/status`. Selección `auto` prefiere `gpu:0` sólo
  cuando Paddle confirma CUDA; de lo contrario usa CPU.
- Si una inicialización o inferencia GPU falla, el lector reintenta una vez en
  CPU y registra el dispositivo efectivo. Los modelos se liberan al terminar
  cada trabajo para limitar memoria en equipos de 8 GB.
- Instalador OCR separado para CPU y CUDA, con versiones fijadas, validación del
  runtime y descarga opcional de modelos. Sin el componente, se conserva
  exactamente el flujo `needs_ocr`.

## Pendiente por diseño

El orden y los criterios de salida del trabajo restante están definidos en
[`BACKEND_COMPLETION_PLAN.md`](BACKEND_COMPLETION_PLAN.md).

- Expansión restante para familias y partidas del capítulo 72 todavía no
  cubiertas. Con menos de tres opciones, la selección permanece bloqueada en
  `needs_review`.
- Componente frontend para mostrar el PDF lateral, enfocar la página y dibujar
  el resaltado usando el contrato de evidencia ya disponible.
- Validación de calidad OCR y adaptadores geométricos de los cuatro formatos
  reales después de instalar el componente opcional y descargar sus modelos.
- Expansión del motor a todas las ramas del capítulo 72 y a los NICO que exigen
  uso, acabado o propiedades adicionales. La fuente continúa marcada
  `SIN VIGENCIA` y ninguna salida adquiere validez aduanera.
- Validación de volumen, respaldo/restauración y consumo con 8 GB de RAM.
