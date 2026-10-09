# Producto

<!-- impeccable:product-schema 1 -->

## Platform

web

## Propósito y flujo

Cargar actas de molino, consultar datos extraídos, revisar candidatos de fracción y NICO con evidencia y confirmar la clasificación. Consultar después las actas y sus coladas y rollos en un historial con filtros.

## Usuarios

Por confirmar el perfil principal. Supuesto de implementación: personal que revisa certificados y clasificaciones, con acceso a datos técnicos y fundamentos normativos.

## Capacidades y restricciones

Acta → coladas → rollos. Se muestra una fila por rollo agrupada por colada. El usuario autorizó implementar la propuesta de dos secciones: carga y revisión, e historial. El backend determina clasificación, candidatos, factores y permisos de aprobación. Se preservan valores originales, normalizados y evidencia; una sugerencia no equivale a una selección humana.

PDF y XLSX están documentados en el backend. El procesamiento continúa al navegar por las secciones. La API requiere persona y motivo. Por decisión del usuario, el dictamen envía Administrador y un motivo fijo sin campos visibles. La selección de candidatos mantiene sus datos de auditoría; la captura manual usa Administrador y una justificación escrita. Los borradores conservan selecciones registradas; los textos no enviados de formularios no constituyen una revisión guardada.

## Principios

La biblioteca de formatos permite configurar extracción PDF mediante regiones,
campos y columnas sin cambiar reglas jurídicas. Las pruebas preservan actas;
activar requiere ejemplos revisados y sólo habilita futuros trabajos. Reprocesar
es una acción explícita que crea otra revisión. La biblioteca pertenece a la
instancia local y registra persona/motivo; no existe autenticación multiusuario.

Generar clasificación muestra sólo el botón y envía Administrador y un motivo fijo, sin campos de captura, por decisión del usuario.

- Revisar sin cambiar de sección.
- Explicar cada clasificación mediante datos y fuentes disponibles.
- Mostrar información esencial primero y el detalle bajo demanda.
- Mantener el historial organizado por acta, con acceso a sus rollos.

El detalle del acta tiene cuatro secciones: Coladas (vista rápida tras seleccionar una), Extraído (química, ensayos por rollo y evidencia de la colada seleccionada), Validación (sugerencias y captura manual de fracción/NICO por rollo) y Dictamen de clasificación. Se elimina la pestaña Historial dentro del acta; permanece Historial de actas en la navegación principal. La captura manual conserva sugerencias y selecciones previas, valida formato y no constituye verificación normativa automática.

La selección de una sugerencia de fracción/NICO se confirma con Elegir fracción y envía Administrador y un motivo fijo a la API, sin campos de persona ni motivo, por petición del usuario.

Por decisión del usuario, la selección auditada de fracción y NICO confirma la verificación humana de cada rollo. La aprobación del acta cierra la revisión completa; los datos faltantes y factores desconocidos del motor se preservan sin bloquear el cierre. Se mantienen bloqueos de contradicciones y cobertura incompleta.


La sección Cómo se clasifica explica el recorrido del motor, respaldo de sugerencias, incertidumbre y confirmación humana. Es informativa y accesible sin conexión al backend; no modifica reglas ni clasificaciones.

Elegir fracción avanza al siguiente resultado de Validación tras guardar correctamente, en el orden mostrado y sin omitir rollos de la misma colada. La última selección permanece visible; fallos, captura manual y retirada de selección no avanzan.

Por petición del usuario, el dictamen no muestra Guardar borrador. Las selecciones enviadas permanecen guardadas; cambiar un candidato o escribir campos sin enviar no guarda cambios. Se conservan Confirmar acta y Rechazar y el contrato de backend existente.

Desde el acta se puede generar y descargar un Excel de consulta con todos los datos disponibles, coladas, rollos, química, códigos y aprobación, incluso antes de confirmar el acta. Selecciones retiradas y resultados ausentes permanecen explícitos en el reporte.
