# Motor determinista de clasificación — hito 2

## Alcance

Este hito introduce clasificación reproducible para productos laminados planos
del capítulo 72 usando exclusivamente `catalog.json` y las notas extraídas del
PDF proporcionado. La fuente continúa marcada
**DEMOSTRACIÓN — SIN VALIDEZ ADUANERA**.

No se usa IA ni se interpreta un dato ausente como cero. El motor puede resolver
por separado familia del acero, partida, fracción y NICO. Cada nivel no resuelto
queda en `needs_review` con candidatos y campos faltantes.
La ausencia de un metal de recubrimiento tampoco equivale a `coated=false`; el
estado sin revestir debe constar expresamente o capturarse durante la revisión.

## Reglas implementadas

- Definición prioritaria de acero inoxidable: C <= 1.2% y Cr >= 10.5%.
- Umbrales de los demás aceros aleados contenidos en la nota del capítulo para
  Al, B, Cr, Co, Cu, Pb, Mn, Mo, Ni, Nb, Si, Ti, W, V, Zr y otros elementos.
- Acero sin alear sólo cuando todos los elementos necesarios están informados y
  permanecen bajo sus umbrales.
- Selección de partidas candidatas por familia, anchura, laminado y
  recubrimiento: 7208–7212, 7219–7220 y 7225–7226.
- Ramas ejecutables iniciales:
  - 7209 para acero sin alear, ancho >= 600 mm, laminado en frío y sin revestir;
  - 7208 para acero sin alear, ancho >= 600 mm, laminado en caliente y sin
    revestir;
  - 7210.30.02 para cincado electrolítico de ancho >= 600 mm;
  - 7225.50.91 como fracción candidata de otros aceros aleados laminados en
    frío y de ancho >= 600 mm.
- Umbral de alta resistencia inclusivo en 355 MPa.
- Fracción y NICO se validan contra el catálogo antes de persistirse.
- Un código duplicado o ambiguo en la fuente queda en revisión; nunca se elige
  una de sus descripciones por orden de aparición.
- Una fracción candidata de ocho dígitos se expande únicamente con sus NICO
  existentes en el catálogo versionado. Partidas y subpartidas incompletas no
  se presentan como opciones seleccionables.
- Los candidatos de 7225.50.91 filtran contradicciones conocidas de boro,
  espesor, enrollado, porcelanizado y límite elástico.
- Las alternativas de laminados en caliente se reducen según espesor,
  enrollado, relieve y decapado. No se ofrecen fracciones con intervalos de
  espesor incompatibles.
- El orden es estable: resultado demostrado, condición específica coincidente,
  categoría general y especialidades todavía posibles. Se conservan como
  máximo tres opciones.

## Datos faltantes y correcciones

Las actas de ejemplo no informan necesariamente todos los elementos requeridos
para demostrar que un acero es “sin alear”. Por ello una ejecución puede quedar
en revisión aunque el nombre comercial sugiera una clasificación.

`POST /api/v1/certificates/{id}/observations` permite capturar un dato que no
existía. `POST /api/v1/observations/{id}/corrections` reemplaza de forma
inmutable uno existente. Ambas operaciones exigen persona y motivo. Una nueva
reclasificación usa las observaciones vigentes; la ejecución anterior conserva
su instantánea exacta.

## Ejecución e historial

- `POST /api/v1/certificates/{id}/reclassify` crea un trabajo PostgreSQL.
- Cada ejecución enlaza a la anterior mediante `parent_run_id`.
- Cada producto conserva entrada, evidencia, resultado, faltantes, candidatos y
  pasos de decisión.
- `GET /api/v1/classification-runs/{id}` devuelve la reproducción completa.
- Una ejecución incompleta no puede aprobarse.
- Los reportes oficiales continúan incluyendo únicamente ejecuciones aprobadas.

## Revisión de candidatos

Antes de la aprobación, cada producto debe presentar exactamente tres opciones
válidas de fracción y NICO. El personal autorizado selecciona una con nombre y
motivo obligatorios. La selección no equivale a aprobación.

Cada factor de la opción seleccionada debe explicar la regla, el umbral y el
valor observado. También debe enlazar la página y región exactas del PDF para
mostrarlas en un visor lateral. Si no existen tres opciones válidas, la
ejecución queda en `needs_review`; el motor nunca inventa candidatos.

El contrato completo está en
[`CLASSIFICATION_CANDIDATE_REVIEW_REQUIREMENTS.md`](CLASSIFICATION_CANDIDATE_REVIEW_REQUIREMENTS.md).

## Expansión posterior

Faltan las ramas deterministas completas del resto del capítulo 72 y varios
NICO que requieren uso previsto, temple, acabado o propiedades no presentes en
las actas. Se añadirán sólo con reglas de frontera y evidencia de la misma
fuente versionada.
