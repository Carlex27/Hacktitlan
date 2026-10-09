# Referencia de diseño: Finesse UI 1.0

## Fuente y alcance

Referencia elegida por el usuario: [Finesse UI Kit and Design System — Preview](https://www.figma.com/design/jP62p9QhvF7cElZlbqjQoV/?node-id=52-10&p=f).
Consulta del lienzo público: 2026-10-08. Esta es una extracción parcial verificada visualmente, no una exportación de variables ni una reproducción completa del kit.

Se revisaron Typography, Color Scheme, Shadows, Buttons e Inputs. La navegación también muestra Alerts, Avatars, Toggle, Checkboxes, Radio Buttons, Check Circles, Icon Buttons, Segmented Controls, Badges, Tooltips, Snackbars, Pagination, Breadcrumbs, Progress Indicators, Sliders y Dropdowns. Su presencia no demuestra que se hayan inspeccionado sus reglas internas.

Las tablas de tipografía contienen valores legibles en la documentación del lienzo. Colores y componentes se describen por su organización visual; no se atribuyen al kit valores hexadecimales, radios, espaciados ni sombras CSS que no se hayan podido verificar. Figma solicita registro para inspeccionar propiedades detalladas.

## Tipografía verificada

Fuente documentada: **Inter**. [Página Typography](https://www.figma.com/design/jP62p9QhvF7cElZlbqjQoV/?node-id=52-4&p=f).
Los nombres siguientes pertenecen al kit. Tamaño e interlineado están expresados en píxeles de diseño, no en píxeles de la captura ampliada.

| Rol | Variante | Tamaño | Interlineado | Espaciado entre letras |
| --- | --- | ---: | ---: | ---: |
| Title | Large | 120 | 150 | -2% |
| Title | Small | 96 | 120 | -2% |
| Heading | Huge | 72 | 90 | -2% |
| Heading | Extra Large | 60 | 72 | -2% |
| Heading | Large | 48 | 60 | -2% |
| Heading | Medium | 36 | 44 | -2% |
| Heading | Small | 30 | 38 | 0% |
| Heading | Extra Small | 24 | 32 | 0% |
| Body | Extra Large | 20 | 30 | 0% |
| Body | Large | 18 | 28 | 0% |
| Body | Medium | 16 | 24 | 0% |
| Body | Small | 14 | 20 | 0% |
| Body | Extra Small | 12 | 18 | 0% |
| Body | Tiny | 10 | 16 | 0% |

La documentación separa títulos, encabezados de sección y texto de contenido. No se verificaron pesos de fuente ni una escala específica para etiquetas de controles. En una eventual traducción CSS, -2% corresponde a `letter-spacing: -0.02em`; esta conversión no es un token exportado de Figma.

## Colores observados

[Página Color Scheme](https://www.figma.com/design/jP62p9QhvF7cElZlbqjQoV/?node-id=52-6&p=f).

- Bases blanca y negra y una escala de grises de claro a oscuro.
- Escalas separadas para Error (rojos), Warning (amarillos y ocres) y Success (verdes).
- Cada escala ofrece varios tonos, en vez de un único color para todo el componente.

**Aplicación al proyecto:** usar roles semánticos para fondo, texto, borde, acción y estado. Error, advertencia y éxito deben acompañarse de texto o iconos accesibles. No sustituir automáticamente la paleta actual por colores aproximados de una captura.

## Profundidad y estados observados

[Página Shadows](https://www.figma.com/design/jP62p9QhvF7cElZlbqjQoV/?node-id=52-7&p=f).

- La documentación distingue Normal Styles, Hover Styles y Focused Styles.
- Las sombras normales se presentan en Small, Medium y Large.
- Hover y foco muestran tratamientos para Primary, Secondary, Error, Warning y Success.

**Aplicación al proyecto:** conservar una escala limitada de profundidad y distinguir interacción de elevación. El foco debe verse al navegar por teclado; una sombra decorativa no reemplaza su indicador. No crear un `box-shadow` supuestamente exacto hasta inspeccionar sus parámetros.

## Botones observados

[Página Buttons](https://www.figma.com/design/jP62p9QhvF7cElZlbqjQoV/?node-id=52-10&p=f).

- Matriz de variantes de apariencia, tamaño y estado, con una guía de uso separada.
- Se ven botones de relleno oscuro, superficies claras, borde y texto de menor énfasis.
- Hay variantes con esquinas redondeadas y otras en forma de cápsula.
- Se muestran composiciones con texto e iconos al inicio y al final.
- Se ven estados de bajo contraste para controles deshabilitados y tratamientos distintos entre las filas de estados. No se transcribieron todos los nombres de esas filas.

**Aplicación al proyecto:** una acción principal por grupo de decisiones; acciones secundarias con menor énfasis. Usar el mismo componente y sus propiedades para todas las variantes. Mantener dimensiones consistentes entre controles del mismo nivel. Los iconos complementan una etiqueta; un botón de sólo icono requiere nombre accesible. No mezclar cápsulas y rectángulos sin una función definida.

## Campos observados

[Página Inputs](https://www.figma.com/design/jP62p9QhvF7cElZlbqjQoV/?node-id=222-4821&p=f).

La página separa Input field y Text Area Input, con matrices de variantes, guías de notación y Documentation — Inputs. No se verificaron medidas, todos los estados ni contratos de validación de cada variante.

**Aplicación al proyecto:** reutilizar Input y Textarea existentes, mantener etiquetas visibles, ayuda y errores asociados al campo. Distinguir vacío, edición, foco, error y deshabilitado. El placeholder no reemplaza la etiqueta. Estas son reglas del proyecto y de accesibilidad, no una transcripción literal de la documentación del kit.

## Mapeo a la implementación actual

| Referencia | Fuente vigente del proyecto | Regla para futuros cambios |
| --- | --- | --- |
| Tipografía Inter | `apps/desktop/src/styles/globals.css`: Geist Variable | Mantener Geist hasta que se autorice implementar el cambio de fuente. Usar la escala anterior como referencia, no aplicar títulos gigantes a tablas operativas. |
| Paletas y escalas | Variables semánticas de `globals.css` | La fuente de verdad de valores implementados es el CSS. No colocar colores sueltos dentro de componentes. |
| Variantes de botones | `src/components/ui/button.tsx`: default, outline, secondary, ghost, destructive, link | Componer estas variantes; no crear una segunda biblioteca Finesse. El mapeo es del proyecto, no equivalencia exacta de nombres del kit. |
| Sombras y foco | Componentes UI existentes | Conservar foco visible y añadir profundidad sólo para explicar capas. |
| Inputs y textareas | `src/components/ui` | Extender controles existentes antes de crear otros. |

## Uso como memoria del proyecto

En revisión, abrir el acta y las referencias LIGIE en un panel derecho con desplazamiento independiente en pantallas amplias. En pantallas pequeñas, colocarlo debajo de los datos. El visor abre bajo demanda y muestra directamente el PDF, sin pestañas, encabezado de referencia ni barras de herramientas propias. Se cierra desde la acción superior de la página.

Antes de diseñar una pantalla, leer `PRODUCT.md`, `DESIGN.md` y esta referencia. `DESIGN.md` registra decisiones adoptadas; este archivo conserva evidencia y límites de Finesse. Las instrucciones del usuario, las reglas del repositorio y la accesibilidad prevalecen sobre ejemplos del kit.

No adoptar todos sus componentes por estar disponibles. En carga, revisión e historial, priorizar lectura de fracción/NICO, serie, estado y evidencia, con detalle bajo demanda. Conservar los flujos y estados ya acordados.

Para completar una migración fiel faltaría verificar variables exportadas o propiedades inspeccionables: hexadecimales, pesos, radios, paddings, dimensiones, sombras, estados y reglas de componentes todavía no revisados. Registrar aquí cada dato con su fuente antes de convertirlo en token. La vista pública no acredita licencia de redistribución de fuentes o assets del kit; revisar esa licencia antes de incorporar dichos archivos.
