# Hito 7 — Respaldo, volumen y rendimiento

**Fecha:** 8 de octubre de 2026.  
**Estado:** implementación y medición de desarrollo verificadas; aceptación del servidor pendiente.  
**Datos completos:** [HITO_7_MEDICIONES.json](HITO_7_MEDICIONES.json).

## Alcance entregado

- Backup de PostgreSQL, PDF, derivados, reglas y manifiesto con conteos. Conteos,
  archivos referenciados y `pg_dump --snapshot` comparten una transacción
  `REPEATABLE READ`; inserciones posteriores no alteran ese snapshot.
- Verificación SHA-256 de archivos administrados, contenidos del ZIP y segunda
  copia. Publicación por renombrado después de verificar y sincronizar con disco.
  Un ZIP incompleto no se publica como respaldo disponible.
- Fallos de la segunda copia conservan primario, hash y manifiesto en `BackupRun`,
  registran error y permiten recuperación mediante `--retry-secondary`. No se
  elimina el primario ni se informa aprobación de ambas copias cuando una falla.
- Retención independiente de 7 diarios, 4 semanales y 12 mensuales en ambas
  carpetas. Se conserva la política existente de 3 manuales.
- Restauración local con hashes previos, base y carpetas vacías, restauración SQL
  transaccional y comparación posterior de todos los conteos y hashes. Sin endpoint
  remoto ni reemplazo de datos existentes.
- Recuperación de la semana/mes actual cuando falta su respaldo, usando hora local.
  `StartWhenAvailable` y propagación del código de salida mantienen visible un fallo
  en el Programador de tareas.
- Harness reproducible con PostgreSQL desechable, migraciones, volumen de cinco
  años, planes `EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)`, consultas, XLSX, worker,
  consumo de CPU/RAM/E/S, respaldo y restauración.

Se corrigió también la configuración de `statement_timeout`: ahora se aplica en
autocommit y deja la conexión sin una transacción implícita. La transacción previa
impedía configurar el aislamiento requerido por el snapshot de respaldo.

El snapshot compartido mantiene la vista del dump mientras siga abierta su
transacción, según la [documentación PostgreSQL 18](https://www.postgresql.org/docs/18/functions-admin.html#FUNCTIONS-SNAPSHOT-SYNCHRONIZATION).
La restauración usa la opción transaccional documentada de
[pg_restore](https://www.postgresql.org/docs/18/app-pgrestore.html).

## Equipo y datos

Windows 11 x64, Intel Core Ultra 9 285H, 16 procesadores lógicos, 32,182 MiB de RAM
física y PostgreSQL 18. El equipo medido no es un servidor de 8 GB.

Se sembraron **18,250 actas**, **273,750 coladas** y **273,750 rollos**, distribuidos
en 1,825 días desde el 9 de octubre de 2021. Cada rollo incluye un candidato, factor,
enlace de evidencia y observación; cada colada, un elemento químico. La siembra
tardó **38.717 s**. La carga posterior añadió 40 actas y 571 coladas/rollos, por lo
que el respaldo/restauración final contiene 18,290 actas y 274,321 coladas/rollos.

El histórico comparte un único PDF pequeño; los 40 documentos de carga tienen
contenido sintético distinto. Este conjunto prueba volumen relacional, no tamaño
realista del archivo documental. No valida precisión química ni legal del motor.

## Resultados

Diez muestras por consulta, p95 por rango más cercano. TestClient ejecuta la API
real, pero no añade transporte TCP ni Tailscale.

| Consulta | p95 (ms) |
|---|---:|
| Listado | 15.015 |
| Día | 6.822 |
| Semana | 5.787 |
| Mes | 5.530 |
| Número de acta | 7.903 |
| Fabricante | 13.213 |
| Colada | 151.297 |
| Rollo | 144.468 |
| Fracción y NICO | 146.024 |
| Aprobación | 49.754 |
| Procesamiento | 15.450 |
| Fecha de carga | 18.743 |
| Detalle del acta | 19.344 |
| Detalle de clasificación | 22.341 |
| Página por cursor | 19.591 |

| Trabajo del worker | Duración (s) | RAM máxima del proceso (MiB) | API simultánea p95 (ms) |
|---|---:|---:|---:|
| XLSX: 10 actas / 150 rollos | 0.421 | 112.03 | 15.266 |
| XLSX: 100 actas / 1,500 rollos | 1.112 | 149.79 | 17.629 |
| XLSX: 300 actas / 4,500 rollos | 3.058 | 235.97 | 17.305 |
| Persistencia: 10 actas, 10–15 coladas por acta | 0.820 | 105.86 | 14.979 |
| Persistencia: 30 actas, 15 coladas por acta | 2.594 | 106.12 | 16.459 |

Cada exportación y trabajo terminó en `succeeded`. El JSON registra CPU y bytes
de E/S de cada proceso worker. CPU incluye su arranque; RAM es el pico del proceso,
no la memoria total del servidor. No se ejecutó una exportación XLSX única de los
273,750 rollos; se midieron lotes diario, ráfaga y mensual sobre ese histórico.

| Operación | Resultado |
|---|---|
| Tamaño de base después de la carga | 554,301,119 bytes |
| Respaldo completo y segunda copia | 3.218 s |
| Tamaño del ZIP | 5,353,451 bytes |
| SHA-256 del ZIP | `01dd9f0f1d8a65c2185ebe88f1cc19e05b1c8750d49eadc977ccdc5a36376a28` |
| Restauración en base vacía | 19.479 s |
| Conteos de las 23 tablas y hashes de archivos | Iguales al manifiesto |

Los planes muestran lecturas secuenciales para búsquedas por subcadena en coladas
y rollos, y para el filtro de clasificación con muchos resultados coincidentes.
El listado/cursor usa ordenación por `coalesce(fecha_acta, fecha_carga::date)`;
los índices existentes sobre las fechas separadas no eliminan esa ordenación.
Se conservaron los índices actuales y no se aumentaron recursos: primero hace
falta acordar el objetivo de latencia y repetir la medición en el servidor.

## Pruebas y límites de aceptación

**349 pruebas aprobadas**, con dos advertencias existentes (TestClient/httpx y
ccache/Paddle). Los 24 casos nuevos comprueban archivo y copia, retención,
ausencia/espacio/corrupción del secundario, recuperación, rutas inseguras,
programación, métricas, volumen válido y restauración PostgreSQL real. La prueba
de integración inserta un fabricante después de exportar el snapshot y verifica
que no altera sus conteos. Compilación Python y sintaxis PowerShell verificadas.

Para ejecutar todo con PostgreSQL, incluir sus utilidades en `PATH` y ejecutar
`uv run pytest`. La prueba de restauración se omite explícitamente si faltan esas
utilidades o la conexión a `hacktitlan_test`.

Quedan pendientes:

1. Tiempos máximos acordados y ejecución en el servidor de demostración, incluyendo
   el equipo mínimo de 8 GB cuando corresponda. No hay objetivo de latencia
   inventado ni aceptación automática del servidor.
2. Duración/CPU/RAM de OCR con un PDF escaneado real y respuesta de API simultánea.
   El harness admite `--ocr-pdf`; las pruebas de persistencia usan extracción
   controlada y no prueban OCR.
3. Arranque real de Windows después de estar apagado a las 02:00. No había una tarea
   `Hacktitlan-DailyBackup` instalada en el equipo de medición; sólo se verificó
   el contrato del instalador y la recuperación de períodos.
4. Desconexión física y espacio insuficiente de una unidad secundaria independiente.
   Los fallos se inyectaron en pruebas; la copia real se verificó en otra carpeta
   del mismo disco.

El Hito 7 permanece **en validación**, conforme a la regla de avance del plan.
