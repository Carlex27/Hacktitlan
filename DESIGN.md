# Diseño de la interfaz de revisión

En actas abiertas, Quitar selección de fracción y NICO devuelve el rollo a Requiere
revisión y conserva su historial. Elegir una sugerencia no bloquea la captura manual:
puede sustituirse por códigos propios con justificación. El cierre completo del acta
bloquea ambas formas de edición y la retirada de la selección.

## Datos extraídos principales

Por petición del usuario, la tabla en el detalle de colada/rollo conserva sólo
Campo, Valor original y Valor normalizado. Se retiran Verificación local, sus
acciones y el aviso de comparación asociado. Los datos de verificación y las
correcciones guardadas permanecen en el backend.

## Dirección

Interfaz de operación: lectura de datos técnicos, revisión y trazabilidad. Mantener Geist, los componentes React y los tokens existentes. Fondo claro, superficies separadas por bordes discretos, azul para acciones y selección; estados con texto además de color. No añadir fuentes, ilustraciones ni animaciones decorativas.

## Organización

Dos entradas: Carga y revisión, Historial de actas. La carga y la revisión comparten sección; el historial abre el mismo detalle. Una fila por rollo agrupada por colada. Fracción, NICO, serie, descripción, dimensiones y estado en ese orden. Alternativas muestran fracción y NICO conjuntamente y abren la revisión auditada antes de guardar una selección.

## Detalle

Detalle expandido del rollo con química y propiedades de su colada, valores originales y normalizados y explicación del clasificador. Documento original y referencia normativa bajo demanda. El historial conserva una fila por acta y filtra en el servidor, incluyendo colada y serie.

## Estados y adaptación

Carga, vacío, éxito, requiere revisión y error explícitos. Formularios con etiquetas y errores asociados. Controles con foco visible. Tablas dentro de contenedores desplazables sin desbordar la página. Las acciones de aprobación afectan la ejecución completa, nunca sólo el rollo abierto.

## Referencia Finesse UI

El usuario eligió Finesse UI 1.0 como referencia. La extracción verificada y sus límites están en [docs/FINESSE_DESIGN_REFERENCE.md](docs/FINESSE_DESIGN_REFERENCE.md); consultarla antes de diseñar o modificar componentes. No constituye todavía una migración visual.

Adoptar como guía la jerarquía tipográfica, las variantes reutilizables y la separación de estados, colores semánticos y profundidad. Conservar Geist y los tokens actuales hasta implementar explícitamente una decisión de cambio. Los valores implementados se consultan en `apps/desktop/src/styles/globals.css`: actualmente el token `primary` es neutro oscuro; la mención de azul en Dirección describe una intención, no el valor actual del token.

No inventar valores de Figma ni construir una biblioteca paralela. Las reglas de accesibilidad y del flujo de revisión prevalecen sobre una variante visual del kit. Distinguir siempre evidencia de la referencia, adaptación propuesta y decisión implementada.

### Aplicación en Carga y revisión

Archivos enviados retira automáticamente las filas de extracción terminada (`succeeded` y `needs_review`). Conserva trabajos activos, errores y archivos que necesitan OCR. Sólo cambia la presentación de la cola; las actas y su evidencia permanecen guardadas y accesibles desde el historial y Revisión documental.

Generar clasificación conserva sólo el botón en su sección; envía Administrador y un motivo fijo. Los avisos de proceso, resultado y error permanecen visibles cuando corresponden.

Revisión documental muestra actas, fabricante, calidad, conteos de bloqueantes y advertencias y acceso a Revisar. Por petición del usuario, no muestra la lista de incidencias ni el botón Volver a analizar. Conserva Actualizar revisiones y los avisos de trabajos activos.

Aplicadas la jerarquía de encabezado 24/32, texto introductorio 16/24 y texto auxiliar 14/20. La carga usa superficie clara y acción principal oscura; las colas tienen bordes discretos sin sombra. La revisión usa navegación segmentada, controles existentes y colores semánticos en la tabla. Los campos de reprocesamiento y clasificación usan etiquetas legibles y controles de 40 px de alto. Se conserva Geist: esta es una adaptación del sistema de Finesse al producto, no una copia exacta de sus tokens.

### Navegación superior

Por decisión del usuario, las dos secciones pasan de la barra lateral a una barra superior compacta. Nombre de la aplicación a la izquierda y Carga y revisión e Historial de actas a su lado. En pantallas estrechas, las secciones ocupan una segunda fila con sus etiquetas completas. Se reutilizan los tokens existentes de navegación, botones con altura mínima de 44 px, estado activo oscuro, `aria-current` y foco visible. Las migas de pan permanecen debajo y el contenido utiliza todo el ancho disponible. Es una adaptación del proyecto, no una exportación de Finesse.

### Historial de actas

Encabezado 24/32 e introducción 16/24. Búsqueda y resultados se separan con un borde discreto sobre fondo claro, sin tarjetas anidadas. Los filtros mantienen etiquetas visibles y controles de 40 px; la cuadrícula responde al espacio disponible. Cada acta destaca su número, conserva fabricante y fecha, y muestra estado con texto e icono junto a Abrir acta. Actualizar se alinea con el encabezado del listado. Carga con texto y spinner, vacío con orientación contextual y error con reintento. Se reutilizan Geist y tokens semánticos; no se atribuyen estos valores a tokens exportados de Finesse.

### Interior del documento

Para pruebas, Borrar aparece entre Generar clasificación y Actualizar, con la
variante destructive existente. Ejecuta el borrado del acta abierta sin persona
ni motivo, muestra Borrando… y deshabilita el botón mientras espera. Ante error
conserva el acta visible y presenta el mensaje del backend. Al terminar vuelve
al listado, informa el resultado y retira sólo esa acta de la cola de carga.
No incorpora otro sistema visual ni campos adicionales.

Por petición del usuario, el detalle del documento no incluye el bloque Descartar del historial ni su formulario.

Coladas, Extraído, Validación y Dictamen de clasificación comparten superficies claras con bordes discretos y sin sombras decorativas. Encabezados de bloque 18/28, códigos destacados 24/32 y lectura de datos, etiquetas y explicaciones 14 px con interlineado de 20–24 px. Los valores largos se muestran completos; tablas con desplazamiento y foco por teclado, códigos y series sin cortes. Química y propiedades mecánicas usan cuadrículas adaptables.

Validación presenta sugerencias, condiciones con evidencia y captura manual por rollo. La sugerencia no lleva marca de aprobación verde; se elimina el bloque «Justificación de la clasificación» por petición del usuario. Selección neutra con borde y radio; controles y consulta de evidencia reutilizan Button con altura mínima de 40 px. Estados de aprobación traducidos y tipos de producto conocidos con nombres legibles; datos originales y términos desconocidos se conservan.

El dictamen muestra estado, pendientes y acciones; conserva las reglas de autorización y los errores de API. Los rollos y coladas pendientes se consultan en un desplegable. El dictamen ocupa una cuarta sección junto a Coladas, Extraído y Validación; se desplaza con el contenido. No contiene campos de persona o motivo: envía Administrador y motivo fijo al backend, por petición del usuario. El historial de selecciones se conserva en el backend, sin pestaña en el acta.

Los roles warning y success reutilizan los tonos ámbar y esmeralda presentes en el proyecto; son tokens semánticos del proyecto, no valores exportados de Finesse. No se incorporan fuentes, dependencias ni animaciones decorativas.

El selector de alternativas de NICO muestra fracción y NICO en el control compacto. El desplegable reutiliza Radix: código y NICO en la primera línea, descripción completa debajo, selección marcada con check y foco por teclado. Su ancho se limita a 28 rem y al espacio disponible de pantalla; listas largas se desplazan. Elegir una alternativa abre el detalle auditado y no guarda la selección automáticamente.

En Extraído, la química y los ensayos no comparten columnas de igual altura. Los ensayos mecánicos se presentan por serie del rollo usando product_id; los datos sin relación válida se muestran aparte para revisión, sin inferir asociaciones por orden.

Coladas muestra primero los controles de selección y después una tabla rápida de los rollos de esa colada. Extraído conserva esa selección y muestra química, ensayos agrupados por serie, atributos y observaciones sólo para la colada elegida. Datos sin asociación explícita se consultan en Sin colada asociada; no se atribuyen a otra colada. Validación identifica el rollo por su serie y permite una captura manual con fracción, NICO y justificación; informa que valida formato, no validez normativa.

La primera colada se activa automáticamente al cargar el acta en Coladas y Extraído. Una selección explícita del usuario prevalece sobre ese valor inicial.

En Extraído, la tabla permite abrir un rollo haciendo clic en su fila o mediante Ver detalle con teclado. Química, propiedades mecánicas, atributos y observaciones aparecen en una fila de detalle inmediatamente debajo del rollo elegido. Sólo un rollo queda abierto; elegir otro cierra el anterior y repetir la selección lo cierra. No hay bloques técnicos debajo de la tabla. Los datos compartidos corresponden únicamente a su colada y no se mezclan ensayos de otros rollos.
Desde Coladas, Ver detalle abre Extraído con el rollo elegido ya desplegado en su fila.
Datos extraídos principales conserva Campo, Valor original y Valor normalizado. Se retiran la columna Verificación local y las filas de química de esa tabla; la química se consulta en el bloque propio del rollo.

La selección de una sugerencia de fracción/NICO se confirma con Elegir fracción y envía Administrador y un motivo fijo a la API, sin campos de persona ni motivo, por petición del usuario.

Confirmar cada rollo registra su verificación humana. Confirmar acta cierra esa revisión cuando todos los rollos y coladas tienen selección, fracción y NICO; los datos desconocidos del motor permanecen como evidencia. Las contradicciones y factores obligatorios no cumplidos bloquean el cierre y se explican en pendientes.

Al generar clasificación se muestra una barra con el progreso reportado por el trabajo del backend, estado de envío, espera o ejecución y aviso final. Antes del primer reporte no se muestra un porcentaje estimado. Se reutiliza Progress y los tokens existentes.

Al abrir un archivo XLSX, las migas de pan muestran su nombre original completo con extensión, también desde el historial. El número extraído del acta se conserva como dato independiente.

El historial de actas usa también el nombre original del XLSX como título de su fila.

Revisión documental identifica los XLSX por su nombre original, incluso mientras se procesan, con la misma regla del historial y las migas de pan.

Productos clasificados muestra hasta 10 tarjetas por página: dos filas de cinco en pantalla amplia y menos columnas en pantallas estrechas. Si hay más de 10 resultados, muestra flechas anterior/siguiente y el contador de página; navegar conserva la selección y una ejecución nueva reinicia la paginación.

Las migas de pan de sección y acta se integran en la barra superior junto a la navegación principal. En pantalla amplia se alinean a la derecha; con menos espacio pasan a otra línea dentro del mismo encabezado. Conservan ambas acciones de regreso, foco visible y el nombre completo del documento, que puede envolver. Se elimina la franja independiente de migas de pan.

Historial de actas comparte el centrado y padding de Carga y revisión: contenido con max-w-6xl y márgenes automáticos, px-4/py-8 y sm:px-8; encabezado y bloques separados por gap-8.

El detalle del acta comparte max-w-6xl y márgenes automáticos con Carga y revisión e Historial: barras de regreso/visor y secciones/acciones centradas, contenido con px-4 py-8 sm:px-8 y separación de 32 px. Al abrir el visor, el contenido conserva su adaptación al espacio disponible.
