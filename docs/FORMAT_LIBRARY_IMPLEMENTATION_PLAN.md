# Plan de implementación: biblioteca de formatos de certificados

Fecha: 2026-10-09. Estado: etapas 1, 2 y 3 implementadas para campos y tablas simples en una instancia local. Piloto ampliado, continuidad y despliegue en desarrollo pendientes. Evidencia en [audit/FORMAT_LIBRARY_EDITOR.md](audit/FORMAT_LIBRARY_EDITOR.md).

## Objetivo y resultado esperado

Permitir que una persona configure visualmente la extracción de un formato PDF nuevo, pruebe la configuración con otros certificados y active una plantilla reutilizable sin escribir código. La plantilla transforma evidencia documental al modelo normalizado existente; no modifica reglas arancelarias ni aprueba actas.

Prueba de éxito: configurar un formato hoy no cubierto, ejecutar su plantilla sobre al menos dos documentos adicionales con distintos valores y cantidades de rollos, y comprobar valores, unidades, coladas, rollos y evidencia. La cantidad de ejemplos es una puerta de validación inicial, no una garantía estadística de generalización.

## Base existente y alcance

- `certificate_parser/adapters.py`: contrato y registro de adaptadores; actualmente Molino 1 y Calvert.
- `format_profiles.py`: cinco perfiles, algunos con señales particulares de muestras. No ampliar este listado por cada plantilla de usuario.
- `application/certificate_extraction.py`: adaptador específico, normalización, extracción genérica y asistencia opcional. Incorporar aquí la selección de estrategia.
- `domain/document.py`: páginas, dimensiones, rotación, bloques y cajas de coordenadas; reutilizar como representación documental.
- `mill_certificate.py`: normalización común; conservar datos originales y normalizados.
- `application/worker.py`, `persistence.py`: procesamiento y revisiones; extender el flujo existente.
- `classification_engine`: recibe `ProductFacts`; debe conservar su comportamiento para entradas equivalentes.
- `features/document-viewer`: visor PDF mediante iframe y carga de archivo con estados. El iframe no proporciona una superficie controlada de selección.

Primer alcance: PDFs digitales, páginas orientadas correctamente, campos individuales, tablas con encabezados y filas variables y relaciones explícitas por identificador. No fijar número de rollos, elementos o páginas. En la primera entrega, una tabla partida o una estructura no soportada debe producir revisión explícita, sin extracción silenciosamente incompleta.

Posteriormente: anclas más flexibles y tablas continuadas. Las muestras aportadas son escaneadas, por lo que preparación OCR y evidencia orientada deben adelantarse al piloto: no esperar a la etapa 5 para obtener texto. La etapa 5 conserva la ampliación y validación de robustez sobre escaneados. XLSX conserva su flujo actual. No incluir editor de reglas jurídicas, aprendizaje automático, mercado de plantillas ni integración nativa.

Supuestos por confirmar al iniciar implementación: configuración por personal que conoce el certificado; biblioteca compartida en la instancia del backend; primer piloto PDF digital. La atribución de persona/motivo no equivale a autorización. Reutilizar el control de acceso real disponible y definir quién puede activar antes de habilitar esa acción para varios usuarios.

## Flujo frontend propuesto

1. Desde un documento con extracción incompleta, abrir **Configurar formato**. También permitir elegir una plantilla existente si falló el reconocimiento. Mantener accesible la revisión del acta.
2. Crear borrador con nombre, fabricante descriptivo y ejemplo de origen. Mostrar PDF y panel de asignaciones; no pedir parámetros técnicos antes de seleccionar un campo.
3. Marcar campo o tabla. Mostrar texto encontrado y asignar significado mediante opciones del esquema backend. En tablas, asignar encabezados, unidades, escalas y claves de rollo/colada.
4. Probar sin alterar el acta: vista previa con original, normalizado, evidencia y diagnósticos por campo y asociación.
5. Añadir otros documentos de prueba y comparar resultados con valores esperados confirmados por el usuario. Guardar borrador y reanudar.
6. Activar una versión validada. Aplicar al documento mediante reprocesamiento explícito, creando una revisión; activar por sí solo no reprocesa históricos.
7. Biblioteca: buscar, abrir, crear nueva versión y retirar del reconocimiento automático. Conservar versiones utilizadas por extracciones anteriores.

Diseño: modo operativo, componentes y tokens actuales, Geist y referencia Finesse según DESIGN.md. Editor con documento y panel en pantalla amplia; en pantalla estrecha, alternar entre documento y asignaciones sin perder selección. No sustituir el visor de consulta por el editor.

Interacciones: dibujar una caja es una opción; también seleccionar bloques con clic y ajustar límites con controles y teclado. Foco visible, nombres accesibles, errores asociados y anuncio de resultados. Zoom sólo modifica presentación. Diferenciar corregir este documento de guardar una regla para futuros documentos.

Estados explícitos: loading al preparar página o ejecutar prueba; empty sin asignaciones/resultados; success con prueba terminada; needs_review ante faltantes, conflictos o estructura no soportada; error con reintento y borrador conservado. Estos estados de UI no sustituyen el ciclo de vida de la plantilla.

## Modelo backend propuesto

Separar identidad del formato, versiones y ejecuciones de prueba:

- **Formato**: id, nombre, descripción/fabricante, versión activa y fechas.
- **Versión**: número, versión del esquema de configuración, estado draft/active/retired, configuración tipada, hash, autor/motivo y ejemplos. Como máximo una versión activa por formato.
- **Prueba**: versión o revisión exacta del borrador, documento/hash, versión del extractor, resultado, diagnósticos, valores esperados confirmados y fecha.
- **Procedencia de extracción**: id y versión de plantilla, hash de configuración, versión del extractor y hashes de documentos; asociar a la revisión existente.

Usar SQLAlchemy y Alembic existentes. Configuración JSON validada por modelos tipados; relaciones, unicidad y estados controlados en base de datos. Evitar duplicar el PDF: referenciar documentos almacenados. Determinar con el flujo de borrado cómo conservar evidencia mínima de validación sin impedir el borrado solicitado de documentos.

La configuración contiene:

- Señales de reconocimiento estables, selector de página y condiciones de estructura. No usar número de certificado/pedido como identidad del formato.
- Selectores de campo: identificador canónico permitido, página, región, ancla cuando aplique, cardinalidad y unidad/escala declarada.
- Selectores de tabla: región, encabezados, columnas semánticas, identificación de filas y claves de relación. No unir tablas por posición de fila.
- Política explícita de repetición y continuación; una configuración no soportada se rechaza o se informa como pendiente.

Convención geométrica: origen superior izquierdo sobre página orientada, cajas relativas entre 0 y 1, dimensiones y rotación de origen registradas. Convertir centralmente al sistema de DocumentLayout, incluyendo recorte/orientación y transformación inversa. No persistir píxeles de pantalla. Verificar superposición de caja y texto con ejemplos, no sólo la fórmula.

Validación de entrada: coordenadas finitas y ordenadas, página existente, límites de configuración, campos permitidos, unidades/escalas compatibles, identificadores duplicados y referencias inválidas. No permitir código, expresiones ejecutables, rutas de archivo ni regex arbitrarias del usuario en la primera versión.

## Extracción y reconocimiento

Implementar un extractor de plantillas compartido: selección de bloques/regiones → campos y filas → payload común → normalización existente. Mantener esta lógica en backend. El frontend captura y presenta; no interpreta química ni decide relaciones documentales.

Resolver primero una versión seleccionada explícitamente, tras comprobar compatibilidad. Para selección automática, evaluar adaptadores existentes y plantillas activas; no dejar que el orden de registro resuelva dos coincidencias incompatibles. Proponer una prioridad explícita para adaptadores calibrados y marcar ambigüedades relevantes para revisión. Sin coincidencia utilizable, conservar extracción genérica y asistencia actual.

La confianza de reconocimiento no es confianza de lectura. Informar ambas por separado. Campos ausentes permanecen desconocidos; conflictos, coladas sin clave y filas sin relación generan diagnósticos. No compensar con valores de otra fila ni aprobar por coincidencia visual.

La ejecución fija una versión y hash antes de encolar: si otro usuario activa una versión nueva, el trabajo conserva la elegida. Retirar una plantilla impide usos automáticos futuros sin borrar procedencia histórica. No prometer reproducción exacta si falta la versión del extractor correspondiente.

## API: estado tras la entrega 1

Se inspeccionaron `app.py`, `schemas.py` y el OpenAPI generado con `create_app(...).openapi()`. Los contratos se implementaron en `api/format_schemas.py` y se publican por OpenAPI, incluyendo activación y selección al reprocesar. OpenAPI es la fuente de verdad de cuerpos, respuestas y errores.

| Operación | Ruta propuesta |
| --- | --- |
| Listar/crear formatos | GET/POST `/api/v1/certificate-formats` |
| Consultar formato | GET `/api/v1/certificate-formats/{format_id}` |
| Crear versión | POST `/api/v1/certificate-formats/{format_id}/versions` |
| Leer/editar borrador | GET/PATCH `/api/v1/certificate-format-versions/{version_id}` |
| Preparar páginas y layout del documento | POST `/api/v1/documents/{document_id}/layout-jobs` |
| Consultar layout preparado y páginas | GET `/api/v1/documents/{document_id}/layout` y recurso de imagen por página |
| Ejecutar/consultar prueba | POST `/api/v1/certificate-format-versions/{version_id}/tests`; GET por test_id |
| Leer layout exacto usado por una prueba | GET `/api/v1/document-layouts/{layout_id}` |
| Imagen orientada por página | GET `/api/v1/document-layouts/{layout_id}/pages/{page_number}/image` |
| Leer prueba | GET `/api/v1/certificate-format-tests/{test_id}` |
| Activar/retirar | POST acciones `/activate` y `/retire` sobre versión |
| Confirmar revisión de prueba | POST `/api/v1/certificate-format-tests/{test_id}/confirm` |
| Recuperar pruebas de versión | GET `/api/v1/certificate-format-versions/{version_id}/tests` |

Preparación y pruebas costosas reutilizan jobs, progreso y cancelación. Imagen y layout deben proceder de la misma representación orientada. Reutilizar renderizado backend si es viable; decidirlo en el piloto técnico antes de añadir un renderizador frontend o dependencia. No ejecutar OCR/render completo en cada movimiento del puntero.

Extender el request de reprocesamiento existente con versión de plantilla opcional; conservar compatibilidad de callers. Definir envelopes, paginación, límites y errores en Pydantic/OpenAPI: no encontrado, validación, borrador desactualizado, prueba obsoleta, formato incompatible y conflicto de activación. Un error de infraestructura no es needs_review.

Control de edición optimista con revisión esperada. Activación atómica, sólo si las pruebas requeridas corresponden al mismo hash de configuración; editar invalida su elegibilidad. Estados y códigos finales deben nacer en schemas y probarse en OpenAPI antes de consumirlos desde frontend.

## Organización frontend

Nuevo módulo `src/features/certificate-formats`, con API pública en index.ts:

- Biblioteca y ciclo de vida: lista, detalle, versiones y activación.
- Editor: superficie de página, selección de región, asignación de campo y mapeo de columnas.
- Pruebas: selección de ejemplos, vista previa y diagnósticos.
- Hooks separados para borrador, preparación documental y pruebas/jobs; transformaciones geométricas puras fuera de hooks y con pruebas.

Crear estos componentes sólo si no hay uno reutilizable. Páginas coordinadoras, sin HTTP ni lógica de extracción. DTOs en `src/lib/api/dto`, endpoints en `src/lib/api/endpoints`, modelos de vista dentro del módulo y textos centralizados según el patrón existente. Reutilizar Button, Input, Alert, tablas, estados, transporte y consulta de jobs.

## Entregas y dependencias

### 0. Piloto y contrato geométrico

Elegir un formato real y tres PDFs digitales con valores/cantidades distintos. Revisar ingestión, layout, renderizado, persistencia y jobs. Probar región → texto → evidencia, zoom, rotación y tamaños de página. Entregar configuración mínima y resultados esperados como fixtures; registrar límites. Sin esta correspondencia comprobada, no construir todo el editor.

### 1. Backend de borradores y prueba de extracción

Implementada: migración 0010, borradores tipados, edición optimista, layouts preparados por jobs, imagen orientada, prueba por jobs con snapshot y relaciones explícitas por rollo/colada. Se conservan actas y pipeline de importación; ningún borrador se activa. Alcance de tablas: una tabla detectada completa por región, encabezados exactos y tablas separadas relacionadas por clave. No reconstruye automáticamente la química de dos filas de Calvert ni segmenta paquetes de certificados; esos casos requieren revisión y ampliación del piloto.

Migraciones, modelos tipados, servicios de formato, extractor de campos/tablas simples y prueba sin persistir actas. Agregar preparación de layout y endpoints con esquemas OpenAPI. Pruebas de contrato, geometría, unidades, escalas, filas variables, relaciones y errores. Actualizar runbook y estado del backend en el mismo cambio.

Aceptación verificada en PostgreSQL de pruebas: una configuración usa el normalizador existente, conserva evidencia y valores originales, y un fallo/cancelación no modifica datos del acta. Se comprobó además vista previa sobre el OCR real ya obtenido de una página del piloto. Pendiente despliegue de migración/API/worker en la instancia de desarrollo y validación del editor en la etapa 2.

### 2. Editor web completo sobre el backend

Implementada: acceso desde acta PDF y Biblioteca de formatos, borradores,
regiones orientadas, ajuste por porcentajes, bloques por teclado, campos,
columnas y claves explícitas, zoom, preparación/pruebas con progreso/cancelación,
comparación de valores y confirmación frente al layout exacto. Errores conservan
las asignaciones locales; el borrador guardado se recupera tras navegar/recargar.

Acceso desde revisión, creación/guardado/reanudación, selección accesible, mapeo de tablas y pruebas con ejemplos. Mantener biblioteca inicialmente limitada a borradores hasta cerrar activación.

Aceptación: usuario configura el piloto sin código, compara extracción y conserva borrador después de errores; estados y navegación funcionan en navegador.

### 3. Activación y uso automático

Implementada para confianza local: tres PDFs con hashes distintos y pruebas
confirmadas success de la configuración/extractor actuales; dos encabezados
estables distintos; activación serializada con unicidad de versión activa,
retirada e historia mínima de validación. Selección automática conservadora con
prioridad para adaptadores calibrados, ambigüedad explícita, snapshots en jobs y
selección explícita compatible al reprocesar. No hay usuarios/roles autenticados
en el producto existente; la apertura a un servicio remoto sigue fuera de alcance.

Activación transaccional, biblioteca/versiones, reconocimiento estable, conflictos y versión fijada en jobs. Integrar worker, persistencia, auditoría y reprocesamiento; conservar las revisiones actuales y el clasificador. Implementar controles de acceso acordes al despliegue.

Aceptación: nuevos documentos usan la versión activa compatible; formato ambiguo va a revisión; reprocesar genera revisión nueva; cambios concurrentes no alteran trabajos en curso.

### 4. Variaciones y continuidad

Ampliar anclas relativas, encabezados desplazados, tablas multipágina, repeticiones y distinto orden de columnas con ejemplos reales. Ampliar corpus negativo y regresiones antes de habilitar cada capacidad.

Aceptación: no se pierden ni duplican rollos al continuar tablas, ni se mezclan químicas entre coladas.

### 5. Escaneados y OCR

Reutilizar runtime OCR existente, verificar orientación/escala, calidad de lectura y correspondencia de evidencia. Mantener vista de original y pendientes. Tratar resultados inciertos como revisión; una plantilla no corrige por sí misma OCR ilegible.

Aceptación: comparación con muestras anotadas y fallos explícitos ante lectura insuficiente; cancelación y progreso operativos.

## Validación y cierre por entrega

- Backend unitario: esquema, geometría, selección, anclas, tablas, unidades/escalas, desconocidos y reconocimiento ambiguo.
- Backend integración: migración, CRUD, edición concurrente, activación/pruebas obsoletas, jobs, cancelación, revisión nueva y procedencia preservada.
- Regresión: adaptadores actuales, extractor genérico, XLSX, normalización y clasificación. Igual ProductFacts debe dar igual decisión.
- Corpus: ejemplos positivos con distintos números de filas y negativos del mismo fabricante con diseño diferente. Comparar valores y relaciones, no sólo estado final.
- Frontend: transformaciones y componentes reutilizables; integración del flujo crear → marcar → asignar → probar → guardar → activar y manejo de errores.
- Navegador: loading/empty/success/needs_review/error, teclado, alternativa al arrastre, foco, contraste, zoom y pantallas amplias/estrechas. Declarar límites no comprobados.
- Estáticas: comandos existentes de typecheck, lint y build web; pytest pertinente. No condicionar estas entregas a Tauri.

Cierre global: el piloto pasa por UI y backend reales, las pruebas corresponden a la configuración activada, el procesamiento conserva originales/evidencia, los fallos son visibles y ningún documento histórico cambia sin reprocesamiento explícito.

## Decisiones pendientes y riesgos

Antes de construir: formato piloto, calidad digital/escaneada, acceso a ejemplos adicionales, alcance de usuarios/activación y viabilidad del renderizado existente. Confirmar requisitos de tablas compartidas y multipágina al inspeccionar muestras; no asumir que todo cabe en una página.

Riesgos principales: asociación errónea de coladas/rollos, coordenadas desalineadas, falsos reconocimientos y pruebas demasiado similares. Mitigaciones: claves explícitas, contrato geométrico probado, condiciones estables, ejemplos negativos y separación entre prueba, activación y aprobación del acta.

No estimar fechas hasta completar el piloto: el costo depende principalmente de las tablas y calidad documental, no de dibujar rectángulos.
