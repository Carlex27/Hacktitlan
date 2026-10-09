# Piloto de biblioteca de formatos — 2026-10-09

Estado: en curso; no constituye una plantilla activa ni valida extracción OCR.

## Muestras inspeccionadas

Ubicación indicada por el usuario: `C:\Users\ofici\Downloads\Downloads`. No se copiaron los originales al repositorio ni se modificaron.

| Archivo | Páginas | Capa de texto |
| --- | ---: | --- |
| ALUMINIZE 1233 (B).pdf | 6 | Ausente |
| ALUMINIZE 1233 (H) I.pdf | 103 | Ausente |
| ALUMINIZE 1233 (H) II.pdf | 76 | Ausente |
| COLD ROLL 1233 (B) BRA.pdf | 20 | Ausente |
| COLD ROLL 1233 (B).pdf | 15 | Ausente |
| HOT ROLL PICKLED & ... 1233 (H).pdf | 4 | Ausente |

pdfplumber encontró cero caracteres en los seis archivos. PdfPlumberReader conserva estas páginas como unreadable; no deben confundirse con campos vacíos. Todas las páginas inspeccionadas por el lector tienen tamaño 612 × 792 puntos y rotación PDF 0.

Revisión visual: primeras páginas de los seis archivos son portadas de Calvert. Se inspeccionaron adicionalmente páginas 2–4 de ALUMINIZE (B), COLD ROLL (B) y HOT ROLL PICKLED. La página 2 contiene encabezados, dimensiones y química; página 3 contiene ensayos y continuación; página 4 puede ser otra portada o una carta. No asumir página fija como reconocimiento ni tratar todo el archivo como una única tabla/certificado.

Piloto candidato: estos tres archivos cortos, comenzando por página 2 de COLD ROLL (B). Pendiente verificar por OCR si sus diferencias admiten una plantilla o requieren variantes. Los paquetes de 76 y 103 páginas requieren segmentación y límites de trabajo antes de ensayos completos.

## Base implementada

`certificate_parser/regions.py` define PageRegion con validación de límites, área positiva y números finitos; conversión bidireccional sobre PageLayout ya orientado; selección de bloques completos y evidencia de bloques cortados.

select_region conserva texto, coordenadas, página, fuente y confianza originales. success sólo significa selección completa, no validación del dato. Una región sin bloques es empty, una palabra cortada es needs_review y una página sin lectura es needs_ocr. No reconstruye tablas ni clasifica productos. No se conecta aún a endpoints ni altera el pipeline activo.

Se comprueban geometría, dimensiones, límites, rotaciones sobre layout orientado, escala de página, redondeo, palabras cortadas y fuente OCR. Estas pruebas usan layouts controlados: no demuestran por sí solas correspondencia entre imagen escaneada y OCR real.

## Renderizado y OCR

pdfplumber.to_image está disponible con las dependencias actuales y permitió inspeccionar las muestras sin instalar paquetes. Existe renderizado orientado en OllamaExtractor.page_image; la futura preparación de páginas debe reutilizar/extraer la misma convención, sin acoplar el editor al servicio de inferencia.

probe_ocr_runtime informó runtime habilitado/instalado y dispositivo CPU; el manifiesto de modelos informó not_installed. Se comprobó después caché PaddleX en la carpeta personal: los modelos estaban disponibles. Se ejecutó OCR local de la página 2 de COLD ROLL (B), rasterizada a 150 DPI, mediante _predict y _convert_results del reader existente. Se obtuvieron 107 bloques, una tabla y rotación 0. No se descargaron modelos ni se ejecutó OCR de los paquetes completos.

Se renderizó y revisó la superposición de las 107 cajas sobre la imagen: alineación visual correcta en esta página sin rotación. Número de certificado y serie contienen el mismo texto `4203023100` en ubicaciones distintas: la selección conserva su caja y confianza, no busca solamente por valor. Colada `2640127`, carbono `0.114` y manganeso `2.71` coincidieron visualmente con esta lectura. Se agregó regresión para distinguir los dos bloques con valor idéntico. No constituye validación de toda la química ni una verdad de referencia confirmada por el usuario.

Las regiones exploratorias demasiado estrechas cortaron bloques y produjeron needs_review, conservando las lecturas completas y reportando los bloques parciales. La química abarca dos filas de elementos; no se puede interpretar como una única fila plana por posición. Artefactos de inspección locales fuera del repositorio: format-pilot-page.png, format-pilot-ocr.json y format-pilot-evidence.png en la carpeta de visualizaciones de esta conversación. No se expone API nueva en esta entrega.

## Próximo criterio de cierre

1. Ampliar el OCR a los otros dos documentos candidatos y a sus páginas de ensayos; registrar configuración/versiones. La lectura de una página y su superposición ya se comprobaron.
2. Comparar imagen orientada, cajas y texto para número de certificado, serie, colada y valores químicos; conservar errores e incertidumbre.
3. Confirmar segmentación de certificados y relación entre páginas de química/ensayos mediante claves.
4. Definir fixture esperada con revisión humana antes de usarla como criterio de activación.
5. Implementar preparación/layout y prueba backend, seguida del editor web.

La etapa 0 sigue abierta hasta ampliar esa correspondencia a los otros ejemplos y sus páginas de ensayos.

## Entrega 1 — backend de borradores y pruebas

Implementados esquema tipado de configuración, biblioteca/versiones, edición con revisión esperada, preparación de layout por job, consulta de layout exacto e imagen orientada y pruebas aisladas por job. Migración 0010 aplicada sólo en hacktitlan_test; Alembic check no detectó diferencias entre metadatos y esquema migrado.

La vista previa reutiliza normalize_certificate y conserva desconocidos: no infiere form ni coiled de la ausencia de datos. Escalas y unidades son explícitas. Los ensayos se relacionan por serie y la química por una clave configurada, nunca por orden de filas. Claves duplicadas, contradicciones, tablas cortadas, encabezados ambiguos y páginas sin mapear producen revisión. La evidencia de una celda de tabla tiene alcance table, no una caja de celda inventada; los campos por zona conservan bloques y confianza originales.

Sobre el OCR del piloto previamente guardado se seleccionaron seis zonas de página 2: número de certificado y serie 4203023100 en ubicaciones distintas, colada 2640127, espesor 1.200 mm, C 0.114 % y Mn 2.71 %. La nueva vista previa devolvió serie/colada correctas, espesor 1.2 y ambas composiciones; se guardó format-pilot-template-preview.json en visualizaciones locales, sin copiar el original al repositorio. Esto prueba campos individuales en una página, no cobertura de los 15 folios ni una plantilla Calvert activable.

Pruebas de integración reales en PostgreSQL: crear/editar borrador, preparación, snapshot inmutable de una prueba, edición concurrente obsoleta, error de OCR con reintentos, cancelación en ejecución sin persistencia parcial, imagen con tamaño compatible, CORS/PATCH y borrado del acta con limpieza de sus layouts/pruebas conservando el formato. No se modificaron actas reales.

La revisión amplia detectó una prueba previa fallida: test_molino3_conflicting_ocr_proposal_can_be_accepted_with_audit espera una observación original de carbono 39 que no encuentra. Se reprodujo el fallo en un archivo git archive de HEAD sin los cambios de esta etapa. Se conserva como incidencia previa; no se alteró extracción/validación de Molino 3 para hacer pasar la biblioteca de formatos.

Siguiente entrega: editor web que consuma exclusivamente estos contratos OpenAPI. Activación, reconocimiento automático, anclas y segmentación siguen pendientes según el plan.

Validación de cierre: revisión amplia de backend con 591 pruebas aprobadas,
una omitida por utilidades/credenciales de respaldo y el fallo previo de Molino 3
descrito arriba. Las aserciones de conteo de tablas y revisión migrada se
actualizaron para la nueva biblioteca. Compilación Python y revisión de espacios
sin errores. No se ejecutaron verificaciones de UI en esta entrega de backend.
