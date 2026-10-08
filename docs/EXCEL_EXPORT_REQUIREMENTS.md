# Requisitos de visualización y exportación a Excel

## 1. Visualización dentro del software

La información persistida debe poder consultarse dentro de la aplicación antes
de exportarla. Como mínimo deben existir:

- historial por día o rango de fechas;
- listado filtrable de actas de molino;
- detalle del acta con sus coladas y rollos;
- detalle de la colada con composición, propiedades, productos y evidencia;
- resultado por rollo con tipo de producto, fracción, NICO y explicación;
- estados visibles de procesamiento, revisión y conflicto;
- acceso a clasificaciones y correcciones anteriores sin sobrescribirlas.

Las listas deben tener búsqueda, filtros, ordenamiento y paginación desde el
backend. El frontend sólo representa los resultados recibidos mediante la API.

## 2. Alcance seleccionable de la exportación

El usuario debe disponer de una acción visible **Exportar a Excel** desde:

- un acta individual;
- una colada individual;
- una selección de actas o coladas;
- los resultados de una consulta o rango de fechas;
- una ejecución histórica concreta.

Antes de generar el archivo se debe mostrar el alcance, filtros aplicados,
cantidad de actas, coladas y productos, y la ejecución de clasificación que se
usará. Exportar no debe alterar datos ni ejecutar una reclasificación implícita.

## 3. Estructura mínima del libro

El archivo `.xlsx` debe funcionar como una fotografía autocontenida y auditable.
Debe incluir las siguientes hojas cuando existan datos aplicables:

1. **Resumen:** alcance, filtros, fecha de generación, versión de reglas,
   cantidades, advertencias y leyenda de estados.
2. **Actas:** identificador interno, número de acta, fabricante, fechas, estado
   y referencia al archivo fuente.
3. **Coladas:** identificador interno, acta relacionada, número de colada,
   norma, grado y propiedades compartidas.
4. **Rollos:** identificador, acta, colada, dimensiones, peso, tratamiento,
   recubrimiento y demás información del producto.
5. **Composición:** una fila por elemento observado, indicando alcance de colada
   o rollo, valor original, valor normalizado, unidad, herencia y confianza.
6. **Clasificación:** una fila por producto y ejecución con tipo, fracción,
   NICO, descripción, estado y versión de reglas.
7. **Evidencia:** campo, valor, página, coordenadas, texto fuente y observaciones
   de revisión.
8. **Auditoría:** correcciones manuales, usuario, motivo, fecha y referencia a
   la ejecución afectada.

Una colada puede tener rollos con clasificaciones diferentes. El libro debe
mostrar la clasificación por producto y no forzar una sola fracción o NICO para
toda la colada.

## 4. Vinculación interna

- Todas las hojas deben compartir identificadores estables como
  `certificate_id`, `heat_id`, `product_id` y `classification_run_id`.
- Las celdas de identificación visibles deben incluir hipervínculos internos
  hacia la fila o sección relacionada cuando esto mejore la navegación.
- La hoja Resumen debe enlazar con las tablas de detalle.
- Las relaciones deben permanecer utilizables sin acceso a PostgreSQL ni a
  Tailscale.
- No se deben usar posiciones de fila como identidad de negocio.
- Los enlaces al PDF original son complementarios: la evidencia esencial debe
  permanecer descrita dentro del libro porque el archivo fuente puede moverse.

## 5. Diseño y usabilidad

- Encabezados, colores, tipografía y formatos numéricos consistentes.
- Tablas de Excel con autofiltros, bandas de filas y nombres estables.
- Encabezados congelados y anchos de columna legibles.
- Fechas, porcentajes, milímetros, kilogramos y MPa con formatos y unidades
  explícitos.
- Colores de estado accesibles acompañados siempre por texto; el color no puede
  ser el único indicador.
- Advertencias y campos `unknown` visibles; un dato ausente nunca se representa
  como cero.
- Evitar celdas combinadas dentro de tablas de datos, macros y dependencias
  externas.
- La presentación debe seguir siendo legible al imprimir o convertir a PDF.

## 6. Generación y auditoría

El backend genera el libro; el frontend solicita la exportación, muestra su
progreso y permite elegir la ubicación final. Cada exportación debe registrar:

- persona solicitante y equipo registrado automáticamente;
- fecha y zona horaria;
- filtros y alcance;
- identificadores de las ejecuciones incluidas;
- versión de reglas;
- nombre, tamaño y hash SHA-256 del archivo generado.

El nombre sugerido debe ser descriptivo y seguro, por ejemplo
`clasificacion_YYYY-MM-DD_acta-123.xlsx`.

## 7. Validación del archivo

Antes de entregar el archivo, el backend debe comprobar:

- que abre como `.xlsx` válido;
- que no contiene errores de fórmula;
- que los conteos de actas, coladas y productos coinciden con la consulta;
- que cada producto referencia una colada y un acta existentes;
- que las fracciones y NICO pertenecen a la ejecución seleccionada;
- que los hipervínculos internos apuntan a destinos existentes;
- que los valores originales, normalizados y desconocidos se conservan.

