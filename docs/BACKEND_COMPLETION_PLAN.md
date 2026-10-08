# Plan de finalización del backend

## 1. Objetivo

Este documento define el trabajo restante para terminar el backend de la
aplicación. Parte del estado registrado en
[`BACKEND_IMPLEMENTATION_STATUS.md`](BACKEND_IMPLEMENTATION_STATUS.md) y no
reemplaza el plan inicial. La prioridad inmediata es explicar individualmente
cada candidato. Después se termina y valida OCR, se fortalece la extracción de
formatos desconocidos y se completa clasificación, operación, rendimiento y
empaquetado.

La primera versión se considera terminada cuando puede recibir un acta digital
o escaneada, conservarla, extraer sus productos con evidencia, producir tres
opciones válidas cuando las reglas lo permitan, registrar una selección humana,
aprobarla, consultarla, exportarla y recuperarla desde un respaldo.

El modelo generativo local permanece como una extensión opcional posterior. No
es requisito para declarar funcional el backend determinista.

## 2. Estado de partida

Ya existen:

- API FastAPI, PostgreSQL, Alembic, almacenamiento central y cola de trabajos;
- carga, deduplicación, revisiones, historial, correcciones y aprobación;
- cuatro parsers conocidos y contrato normalizado común;
- motor inicial del capítulo 72, candidatos, selección auditada y evidencia;
- exportación XLSX, respaldo, restauración y scripts operativos;
- adaptador opcional PP-StructureV3, diagnóstico CPU/GPU e instalador OCR;
- 21 tablas y 72 pruebas aprobadas al crear este plan.

OCR quedó parcialmente terminado. El código y el instalador existen, pero aún
faltan completar la descarga controlada de modelos, ejecutar pruebas reales con
los documentos proporcionados, calibrar geometría y medir consumo en el equipo
objetivo de 8 GB.

## 3. Orden obligatorio

Los hitos se ejecutarán en este orden porque cada uno produce contratos que usa
el siguiente:

1. explicación individual por candidato;
2. cierre técnico de PaddleOCR/PP-Structure;
3. extracción genérica de formatos desconocidos;
4. calidad y revisión documental;
5. cobertura completa de reglas aprobadas;
6. consultas, reportes y auditoría final;
7. respaldo, volumen y rendimiento;
8. seguridad operativa y despliegue por Tailscale;
9. empaquetado e instalación en Windows;
10. aceptación y cierre del backend v1;
11. modelo generativo local opcional.

No se debe iniciar el modelo generativo antes de medir el OCR y cerrar el flujo
determinista. Ningún modelo puede sustituir normalización, validación,
clasificación o aprobación humana.

### Seguimiento

| Hito | Estado |
|---|---|
| Explicación individual por candidato | Completado |
| Cierre técnico de PaddleOCR/PP-Structure | Completado |
| Extracción genérica de formatos desconocidos | En corrección |
| Calidad y revisión documental | Pendiente |
| Cobertura final del motor | Pendiente |
| Consultas, reportes y auditoría | Pendiente |
| Respaldo, volumen y rendimiento | Pendiente |
| Seguridad y Tailscale | Pendiente |
| Empaquetado Windows | Pendiente |
| Aceptación del backend v1 | Pendiente |
| Modelo generativo local | Opcional posterior |

## 4. Hito inmediato: explicación individual por candidato

**Estado: completado.** Migración `0004_candidate_factors`, contrato API y
pruebas incorporados.

### Objetivo

Cada una de las tres opciones debe explicar por qué permanece válida. Los pasos
generales del producto no son suficientes: cada candidato necesita sus propios
factores, condiciones y evidencia.

### Trabajo

- Crear una entidad inmutable para factores de candidato, vinculada a
  `classification_candidates`.
- Guardar regla, operador, umbral, valor observado, unidad y resultado de cada
  condición.
- Distinguir condiciones `matched`, `unknown`, `not_matched` y `conflict`.
- Guardar condiciones obligatorias pendientes de verificación humana.
- Registrar por qué se descartó cada candidato que no llegó a las tres opciones.
- Enlazar cada factor con observaciones exactas mediante `evidence_links`.
- Enlazar reglas normativas con conjunto, versión, hash, página y localizador de
  la fuente cuando esté disponible.
- Evitar copiar todos los pasos generales dentro de cada candidato. Los factores
  comunes deben reutilizar referencias inmutables.
- Ampliar `GET /api/v1/classification-runs/{run_id}` para devolver factores
  agrupados por candidato.
- Añadir consulta de detalle de candidato mediante identificador administrado.
- Bloquear la selección si el candidato contiene una contradicción.
- Permitir una opción condicional sólo cuando señale claramente qué debe
  verificar el personal autorizado.
- Conservar la selección y aprobación como eventos distintos.

### Pruebas

- El mismo snapshot y versión de reglas producen los mismos candidatos y
  factores en el mismo orden.
- Titanio en 0.049999 %, 0.05 % y 0.050001 % prueba la frontera inclusiva.
- Cada factor químico enlaza únicamente la observación del elemento correcto.
- Un candidato contradictorio no puede seleccionarse.
- Un candidato de otra ejecución o producto devuelve conflicto.
- Una nueva selección conserva la anterior.
- OpenAPI contiene todos los campos y errores del contrato.

### Criterio de salida

La API puede reconstruir de forma independiente por qué cada opción fue
ofrecida, qué falta verificar y qué evidencia respalda cada factor.

## 5. Cierre de PaddleOCR y PP-Structure

**Estado: completado.** Manifiesto tipado, OcrModelManager fuera del repo,
geometría con rotación, smoke-check API, worker progresivo/cancelable y
validación del corpus real incorporados.

### Objetivo

Terminar el componente OCR opcional sin afectar la aplicación base. CPU debe
funcionar en equipos con 8 GB; una GPU NVIDIA compatible debe usarse cuando la
prueba local confirme CUDA.

### Trabajo de instalación

- Completar la descarga de PP-StructureV3 en una carpeta administrada fuera del
  repositorio.
- Registrar manifiesto de modelos: versión, licencia, tamaño, idioma, backend y
  SHA-256.
- Reanudar descargas parciales sin publicar un paquete incompleto.
- Verificar espacio libre antes de descargar.
- Añadir reparación, actualización y eliminación del paquete.
- Mantener perfiles CPU y CUDA mutuamente excluyentes.
- Validar que el backend pueda iniciar sin PaddleOCR instalado.

### Trabajo de ejecución

- Ejecutar una prueba corta después de instalar el runtime.
- Registrar dispositivo solicitado, dispositivo efectivo, versión y tiempo.
- Reintentar una vez por CPU cuando falle GPU.
- Limitar hilos, tamaño de lote, resolución y páginas concurrentes.
- Procesar páginas secuencialmente con 8 GB de RAM.
- Liberar modelos después del trabajo o por inactividad.
- Informar progreso por página mediante el trabajo PostgreSQL.
- Permitir cancelación segura entre páginas.
- Conservar el PDF y terminar como `needs_ocr` cuando falte el componente.

### Geometría y contrato

- Normalizar coordenadas OCR a un sistema único por página.
- Guardar ancho, alto, rotación, origen y unidad de cada página.
- Transformar regiones correctamente en páginas rotadas.
- Preservar texto, tabla, celda, confianza y relación entre bloques.
- Validar que `evidence_links` pueda enfocar la región correcta.
- Usar página completa como respaldo cuando no exista geometría; nunca inventar
  coordenadas.

### Validación con corpus

- Ejecutar los cuatro PDF de molino proporcionados.
- Comparar texto digital y OCR para evitar OCR innecesario.
- Validar chino, inglés, números, unidades, símbolos químicos y exponentes.
- Probar el caso `13 × 10^-4 = 0.0013` sin perder valor original.
- Verificar comillas de repetición y herencia de espesor.
- Medir precisión por campo, no sólo precisión global del texto.
- Crear archivos esperados para acta, colada, rollo, composición y propiedades.

### Criterio de salida

Los cuatro PDF completan el flujo en CPU; GPU validada usa CUDA y puede volver a
CPU. Las regiones visuales coinciden con sus campos y el proceso respeta el
límite de memoria acordado.

## 6. Extracción genérica de formatos desconocidos

**Estado: en corrección.** El extractor genérico y el enrutamiento seguro están
implementados. Falta incorporar y registrar los cuatro adaptadores específicos;
un perfil conocido sin adaptador falla de forma segura hacia `needs_review`.

### Objetivo

Aceptar actas distintas de los cuatro formatos conocidos sin depender todavía
de IA generativa.

### Flujo

1. Detectar si el PDF tiene texto digital utilizable.
2. Identificar formato conocido mediante señales, no por nombre de archivo.
3. Usar el parser determinista cuando el formato y su versión coincidan.
4. En caso contrario, ejecutar lectura genérica digital u OCR estructural.
5. Detectar encabezados, tablas, grupos de colada y filas de producto.
6. Mapear etiquetas mediante diccionario versionado y sinónimos.
7. Normalizar unidades, exponentes y valores heredados.
8. Validar el contrato canónico.
9. Guardar datos confiables y enviar incertidumbres a `needs_review`.

### Trabajo

- Crear perfiles de formato independientes de los parsers.
- Calcular una puntuación de detección y registrar señales coincidentes.
- Establecer un umbral mínimo para usar un parser conocido.
- Impedir que una coincidencia débil seleccione una plantilla incorrecta.
- Implementar segmentación genérica por páginas, tablas y encabezados.
- Detectar cantidades dinámicas de actas, coladas, productos y elementos.
- Modelar celdas combinadas, encabezados multinivel y valores repetidos.
- Preservar todos los bloques no mapeados para revisión.
- Permitir corrección manual y posterior reclasificación sin reescribir el OCR.
- Crear fixtures anonimizados por familia de formato.

### Criterio de salida

Un formato conocido conserva su parser actual. Un formato desconocido produce
datos parciales con evidencia y estado explícito; nunca inventa productos ni
marca éxito cuando faltan campos obligatorios.

## 7. Calidad y revisión documental (Completado)

**Estado:** Completado (Hito 4). Auditoría detallada en [`docs/audit/HITO_4_CALIDAD_REVISION_DOCUMENTAL_AUDIT.md`](audit/HITO_4_CALIDAD_REVISION_DOCUMENTAL_AUDIT.md).

### Objetivo

Convertir la extracción en un proceso medible y corregible antes de clasificar.

### Trabajo realizado

- Modelo de dominio `DocumentQualityReport`, `QualityIssue`, `QualityCategory` (`missing`, `low_confidence`, `contradiction`, `anomaly`) y `ProductFamily` en `backend/app/domain/document_quality.py`.
- Detección de campos obligatorios por familia de producto (`flat_rolled_coil`, `flat_rolled_plate`, etc.).
- Cálculo de confianza por campo (< 0.70 umbral mínimo) y procedencia (`digital_text`, `ocr_text`, `inherited`, `manual_capture`).
- Separación estricta de categorías: baja confianza, dato ausente y contradicción física/de dominio (suma química > 100 %, porcentajes fuera del rango [0, 100], dimensiones <= 0, unidades incoherentes).
- Detección de coladas duplicadas contradictorias dentro de la revisión.
- Validación de alcance e integridad relacional: productos huérfanos sin colada registrada, productos y coladas sin química.
- Cola independiente de revisión documental en `GET /api/v1/document-reviews` con filtros y resumen de incidencias.
- Reporte detallado de calidad por acta en `GET /api/v1/certificates/{id}/quality-report`.
- Reprocesamiento multi-etapa en `POST /api/v1/certificates/{id}/reprocess` desde `extraction`, `normalization` o `classification` sin perder historial.
- Compuerta de calidad en `ClassificationService`: las incidencias bloqueantes fuerzan el resultado a `needs_review`, impiden la adivinación de códigos arancelarios y preservan incidencias en `details_json["quality_issues"]`.
- Correcciones registradas como observaciones inmutables (`is_current=True`, `confidence=1.0`), auditadas en `corrections` y sincronizadas con las entidades del acta.

### Criterio de salida cumplido

Ningún producto llega al motor sin contrato válido. Todo dato dudoso conserva
su valor original, motivo y región de evidencia. Validado mediante pruebas unitarias
e integrales completas.

## 8. Cobertura final del motor de clasificación

**Estado:** Completado (Hito 5). Auditoría detallada en [`docs/audit/HITO_5_COBERTURA_REGLAS_AUDIT.md`](audit/HITO_5_COBERTURA_REGLAS_AUDIT.md).

### Objetivo

Completar exclusivamente las ramas respaldadas por la fuente proporcionada y
por datos disponibles en las actas.

### Trabajo

- Crear una matriz de cobertura para cada partida, fracción y NICO del alcance.
- Marcar cada rama como `implemented`, `blocked_by_missing_fact`,
  `ambiguous_source` o `out_of_scope`.
- Incorporar los campos de uso, grado, acabado, temple y proceso que exijan los
  NICO restantes.
- Añadirlos primero al contrato y revisión manual; después a los parsers.
- Evaluar todas las ramas compatibles y conservar motivos de descarte.
- Garantizar tres opciones sólo cuando existan tres opciones legalmente posibles.
- Mantener `needs_review` con menos de tres; nunca completar por similitud.
- Versionar reglas, catálogo, fuentes y pruebas de frontera juntos.
- Prohibir edición de un conjunto aprobado; cualquier cambio crea otra versión.
- Añadir comparación entre versiones antes de reclasificar históricos.

### Pruebas

- Casos justo debajo, en y encima de todos los umbrales.
- Propiedades desconocidas permanecen `null`.
- Códigos duplicados en la fuente no se resuelven por orden.
- Cada candidato existe en el catálogo y pasa sus predicados.
- Un conjunto retirado no inicia nuevas ejecuciones.
- Una ejecución histórica se reproduce con su snapshot y reglas originales.

### Criterio de salida

La matriz no contiene ramas silenciosamente omitidas. Cada elemento del alcance
tiene regla ejecutable o un bloqueo documentado y visible para revisión.

## 9. Consultas, reportes y auditoría final (Completado)

*(Completado y verificado con 9 pruebas unitarias e integración en `test_reporting_and_audit.py`; auditoría de código en `docs/audit/HITO_6_CONSULTAS_REPORTES_AUDITORIA.md`)*

### Trabajo

- Verificar filtros por día, semana, mes, rango, acta, fabricante, colada,
  producto, fracción, NICO y estado.
- Mantener cursores estables bajo inserciones concurrentes.
- Añadir candidatos, selección, factores y evidencia al detalle histórico.
- Mostrar la selección vigente sin eliminar selecciones anteriores.
- Ajustar XLSX para incluir candidato elegido, alternativas, factores y enlaces
  internos hacia evidencia.
- Mantener ocho hojas, formatos, filtros y marca de demostración.
- Impedir reportes oficiales sin aprobación completa.
- Marcar exportaciones preliminares de forma visible.
- Registrar filtros, ejecución, persona, hash y archivo de cada exportación.
- Validar fórmulas, vínculos, apertura y diseño del libro generado.

### Criterio de salida

Un auditor puede partir de un reporte, llegar al producto, reconstruir su
selección y localizar la evidencia original sin consultar tablas manualmente.

## 10. Respaldo, volumen y rendimiento

### Trabajo

- Probar respaldo completo de PostgreSQL, PDF, derivados, reglas y manifiesto.
- Restaurar en una base vacía y comparar conteos y hashes.
- Verificar retención de 7 diarios, 4 semanales y 12 mensuales.
- Probar segunda copia ausente, sin espacio y recuperada.
- Confirmar ejecución pendiente al iniciar después de las 02:00.
- Sembrar 18,250 actas y hasta 273,750 coladas.
- Medir filtros, cursores, detalle y exportaciones sobre cinco años.
- Revisar planes SQL e índices antes de aumentar recursos.
- Probar diez actas diarias de 10 a 15 coladas y ráfagas superiores.
- Medir CPU, RAM, disco, duración OCR y tamaño de base.
- Mantener la API responsiva mientras el worker procesa OCR o exportaciones.

### Criterio de salida

La restauración es reproducible, los hashes coinciden y las consultas cumplen
los tiempos acordados en el equipo servidor de demostración.

## 11. Seguridad y operación por Tailscale

### Trabajo

- Ejecutar la API únicamente en la dirección Tailscale configurada.
- Mantener PostgreSQL fuera de Internet y sin acceso directo del frontend.
- Validar reglas de firewall y scripts de instalación.
- Usar un rol PostgreSQL sin privilegios de superusuario para la aplicación.
- Separar el rol de migraciones del rol de ejecución.
- Impedir rutas proporcionadas por clientes y validar identificadores.
- Limitar tamaño, tipo y estructura básica de archivos cargados.
- Evitar que contenido de PDF u OCR se trate como instrucción del sistema.
- Sanear nombres de descarga y contenido mostrado por el frontend.
- Registrar correlación, trabajo, equipo y errores sin guardar contraseñas.
- Documentar rotación de credenciales de producción aunque la demostración use
  credenciales simples.

### Criterio de salida

Un equipo fuera de la red privada no puede consumir la API ni PostgreSQL. Los
clientes sólo acceden a archivos administrados por identificador.

## 12. Empaquetado e instalación para Windows 11

### Trabajo

- Empaquetar backend y worker como procesos controlados.
- Registrar servicios o tareas con reinicio y logs administrados.
- Incluir migraciones y ejecutarlas una sola vez desde el servidor.
- Comprobar PostgreSQL, Tailscale, carpetas, permisos y puertos.
- Ofrecer aplicación base y OCR como componentes independientes.
- Mostrar tamaño antes de descargar modelos.
- Soportar instalación, reparación, actualización y desinstalación.
- Preservar base, PDF y respaldos durante una actualización.
- Probar una actualización desde la versión anterior.
- Probar equipo CPU de 8 GB y equipo NVIDIA compatible.
- Documentar instalación del equipo principal y conexión del secundario.

### Criterio de salida

Una instalación limpia puede cargar y procesar un PDF. Una actualización no
pierde datos. El equipo secundario opera exclusivamente mediante Tailscale.

## 13. Aceptación y cierre del backend v1

El backend v1 queda terminado cuando se cumplen todos estos puntos:

- todas las migraciones aplican desde una base vacía y desde la versión previa;
- todos los tests unitarios, integración, frontera, golden y restauración pasan;
- los cuatro ejemplos producen resultados reproducibles;
- un PDF desconocido termina procesado parcialmente o en revisión explícita;
- OCR CPU funciona con 8 GB y GPU vuelve a CPU cuando falla;
- cada candidato conserva explicación y evidencia independientes;
- selección y aprobación requieren persona y motivo;
- reportes oficiales incluyen sólo resultados aprobados;
- respaldo y restauración completos están verificados;
- OpenAPI, runbook, arquitectura y estado coinciden con el código;
- no quedan defectos críticos ni migraciones pendientes;
- la marca `DEMOSTRACIÓN — SIN VALIDEZ ADUANERA` aparece en toda salida.

La validación final debe generar un acta técnica con versión, equipo, fecha,
resultados, tiempos, consumo, hashes y limitaciones conocidas.

## 14. Modelo generativo local opcional

Este trabajo inicia sólo después del cierre del backend v1.

### Propósito permitido

- proponer mapeos para etiquetas desconocidas;
- sugerir estructura de tablas difíciles;
- resumir anomalías para revisión;
- proponer candidatos cuando el motor determinista no tenga cobertura.

### Límites

- no decide fracción ni NICO por sí solo;
- no aprueba resultados;
- no modifica observaciones originales;
- no reemplaza PaddleOCR cuando el problema es lectura visual;
- toda salida se marca como propuesta y requiere validación determinista o
  humana.

### Evaluación previa

- construir corpus de formatos reales y casos adversos;
- comparar modelos por precisión de campos, RAM, VRAM, velocidad y licencia;
- probar cuantización en CPU y GPU;
- definir tamaño máximo para 8 GB y perfiles superiores;
- rechazar modelos que inventen valores o no puedan citar evidencia;
- versionar modelo, prompt, parámetros y salida en cada ejecución.

## 15. Regla de avance

Un hito sólo se marca terminado cuando código, migraciones, OpenAPI,
documentación y pruebas relevantes se entregan juntos. Si una prueba depende de
hardware o de un modelo todavía no instalado, el hito permanece pendiente y se
registra el bloqueo exacto; no se simula su aprobación.
