# Revisión de tres opciones de clasificación

## Objetivo

Cada producto debe presentar exactamente tres opciones válidas de fracción
arancelaria y NICO antes de la decisión humana. El sistema no debe completar la
lista con códigos incompatibles, ficticios o sin respaldo en las reglas
versionadas.

Si el motor no puede producir tres opciones válidas, la ejecución queda en
`needs_review`. Debe informar las opciones disponibles, los datos faltantes y
las contradicciones. El personal autorizado debe resolver esos datos antes de
continuar.

## Separación de decisiones

La selección de una opción y su aprobación son eventos diferentes:

1. El motor genera y ordena tres candidatos válidos.
2. El personal autorizado revisa los candidatos y selecciona uno.
3. La selección exige `person_name` y `reason`; el backend registra equipo y
   fecha UTC.
4. El sistema muestra la explicación y evidencia de la opción elegida.
5. El personal autorizado aprueba o rechaza la clasificación mediante un
   evento posterior, también auditado.

La selección no concede por sí misma el estado `approved`. Una clasificación
con datos faltantes, contradicciones o evidencia insuficiente no puede
aprobarse.

Mientras no exista autenticación, `person_name` identifica a la persona
responsable dentro del registro de auditoría. La autorización operativa se
controla mediante el procedimiento del sitio y el acceso privado por Tailscale.
Una etapa posterior podrá sustituir este mecanismo por cuentas y roles sin
perder el historial.

## Candidatos

Cada candidato debe conservar como mínimo:

- identificador estable, posición del 1 al 3, fracción y NICO;
- descripción y versión exacta del conjunto de reglas;
- nivel de respaldo, condiciones cumplidas y datos faltantes;
- contradicciones detectadas y motivos de descarte de otras ramas;
- pasos de decisión y enlaces a sus evidencias.

El orden se obtiene mediante reglas deterministas. Una puntuación sólo expresa
cobertura de evidencia; no representa probabilidad jurídica ni sustituye la
revisión del personal autorizado.

Las fracciones deterministas pueden expandirse con sus NICO del catálogo. Cada
NICO debe pasar filtros de compatibilidad con los hechos conocidos. El sistema
descarta contradicciones de intervalo, composición, forma o proceso antes de
ordenar y limitar la lista a tres.

## Explicación y evidencia

Cada factor debe mostrar regla, operador, umbral, valor observado, unidad y
resultado. Por ejemplo, una decisión basada en titanio debe mostrar el
porcentaje normalizado, el umbral aplicable y la comparación realizada.

Cada factor se vincula únicamente con su evidencia correspondiente. El enlace
debe conservar `document_id`, página, coordenadas, texto original, valor
normalizado y confianza. No se deben adjuntar indiscriminadamente todas las
observaciones del producto a cada paso.

Al seleccionar un factor, la interfaz debe abrir a la derecha el PDF original,
ir a la página indicada y resaltar la región exacta. Si no existen coordenadas,
debe mostrar la página completa con una advertencia explícita. El frontend
nunca recibe ni envía rutas del sistema de archivos.

La interfaz debe distinguir evidencia del acta de molino y evidencia normativa.
Cuando ambas intervengan, debe permitir cambiar entre la región del acta y la
regla fuente.

## Persistencia requerida

El diseño debe incorporar:

- `classification_candidates`, como opciones inmutables de una ejecución;
- `classification_selections`, como historial inmutable de selecciones;
- `evidence_links`, para unir cada paso con observaciones o fuentes normativas;
- `document_pages`, para geometría, rotación y estado de cada página.

Una nueva selección no sobrescribe la anterior. Debe registrarse como otro
evento enlazado. Sólo puede seleccionarse un candidato perteneciente al mismo
producto y ejecución.

## Contrato de API previsto

La API debe permitir:

- consultar los tres candidatos, factores y estado de respaldo;
- registrar una selección con candidato, persona y motivo;
- consultar la evidencia mediante un identificador administrado;
- descargar el PDF mediante `document_id`;
- rechazar selecciones obsoletas o ajenas mediante un error de conflicto.

Los nombres y rutas definitivos de endpoints se documentarán al implementar el
hito. La documentación OpenAPI será el contrato ejecutable de la API.

Contrato implementado para este hito:

- `GET /api/v1/classification-runs/{run_id}` devuelve candidatos ordenados,
  historial de selecciones y pasos por producto.
- `POST /api/v1/classification-results/{result_id}/select` registra una
  selección. El cuerpo exige `candidate_id`, `person_name` y `reason`.
- `POST /api/v1/classification-runs/{run_id}/approve` sólo permite aprobar si
  cada resultado tiene una selección autorizada.
- `GET /api/v1/evidence/{evidence_link_id}` devuelve la observación, documento,
  página, región y URL administrada del PDF. Cuando falta geometría, declara
  `fallback: full_page` en vez de inventar coordenadas.

## Interfaz prevista

La pantalla de revisión tendrá dos paneles:

- izquierda: tres candidatos, selección y factores explicados;
- derecha: visor PDF enfocado en la evidencia activa.

Todos los candidatos y factores deben ser utilizables por teclado, tener nombre
accesible y conservar los estados `loading`, `empty`, `success`,
`needs_review` y `error`.

## Pruebas de aceptación

- El motor entrega exactamente tres candidatos válidos antes de habilitar la
  selección.
- Con menos de tres candidatos, el resultado queda en `needs_review` y no se
  inventan códigos.
- El orden de candidatos es reproducible con las mismas entradas y reglas.
- Los valores situados justo debajo, en y justo encima de cada umbral producen
  el resultado esperado.
- Cada factor abre la página y región correctas del PDF.
- Una selección exige persona y motivo y no equivale a aprobación.
- No puede seleccionarse un candidato de otra ejecución o producto.
- No puede aprobarse una opción con contradicciones, datos obligatorios
  faltantes o evidencia insuficiente.
- El historial conserva candidatos, selecciones, aprobaciones y versiones de
  reglas sin sobrescrituras.

## Estado

Generación, persistencia, selección auditada, bloqueo de aprobación y enlace
exacto paso–observación implementados. El backend ya entrega página, región y
URL administrada para navegación. El componente visual del visor PDF permanece
pendiente del frontend.

La explicación individual quedó implementada mediante `candidate_factors` y
`GET /api/v1/classification-candidates/{candidate_id}`. Cada factor conserva
regla, comparación, valores, resultado y enlaces de evidencia. El motor también
registra por qué descartó opciones evaluadas.
