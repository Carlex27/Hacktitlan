# Estado de implementación del backend

## Implementado

- Runtime Python 3.12 y dependencias fijadas mediante `uv.lock`.
- Configuración tipada, errores estables, respuestas `data/meta/error`, logs
  JSON, correlación y timestamps con zona horaria.
- Esquema PostgreSQL de 18 tablas con `bigint identity`, integridad, índices y
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

## Pendiente por diseño

- PaddleOCR/PP-Structure y modelos locales opcionales. Hasta entonces un PDF
  escaneado termina correctamente en `needs_ocr`.
- Expansión del motor a todas las ramas del capítulo 72 y a los NICO que exigen
  uso, acabado o propiedades adicionales. La fuente continúa marcada
  `SIN VIGENCIA` y ninguna salida adquiere validez aduanera.
- Validación de integración, volumen, respaldo/restauración y 8 GB sobre un
  PostgreSQL 18 nativo. Las pruebas están preparadas para `hacktitlan_test`, pero
  requieren instalar e iniciar PostgreSQL en el equipo servidor.
