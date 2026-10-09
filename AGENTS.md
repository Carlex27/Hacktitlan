# Reglas de desarrollo del repositorio

Estas reglas aplican a todo el proyecto.

## Prioridad actual: UI web

- Primero construir y validar la UI y sus flujos en el navegador, incluyendo
  la integración con el backend, accesibilidad y estados de carga y error.
- Aunque el frontend viva en `apps/desktop`, por el momento el entorno de
  desarrollo y validación es web.
- Posponer Tauri, empaquetado, integración nativa y validaciones de escritorio
  hasta que el usuario indique retomar esa etapa. No condicionar la entrega de
  cambios de UI a verificaciones de Tauri ni señalar su ausencia como pendiente.

## Arquitectura por componentes

- Toda interfaz debe construirse mediante componentes React pequeños,
  reutilizables, tipados y con una sola responsabilidad.
- Las páginas sólo coordinan componentes y casos de uso. No deben contener
  tablas extensas, formularios completos, acceso a archivos, llamadas HTTP ni
  reglas de negocio implementadas directamente en el JSX.
- Los componentes visuales genéricos viven en `src/components/ui`; los
  componentes de dominio viven dentro de su módulo en `src/features`.
- Antes de crear un componente nuevo, comprobar si ya existe uno que pueda
  extenderse mediante propiedades o composición. No duplicar variantes por
  copia y pega.
- La lógica de clasificación, normalización química y validación documental
  pertenece al backend. El frontend sólo captura, presenta y explica datos.
- Los hooks coordinan estado y efectos. Las transformaciones puras deben vivir
  en funciones independientes y tener pruebas unitarias.
- No usar `any`, estados globales implícitos, efectos con dependencias
  incompletas, HTML sin sanitizar ni valores jurídicos codificados en la UI.
- Todos los componentes interactivos deben ser accesibles por teclado, tener
  nombre accesible, estados de foco visibles y mensajes de error asociados al
  campo correspondiente.
- Cada flujo debe modelar explícitamente `loading`, `empty`, `success`,
  `needs_review` y `error`; nunca esconder fallos o datos desconocidos.
- Las listas de rollos son dinámicas. No asumir una cantidad fija de filas,
  coladas, páginas, elementos químicos o certificados.
- Los componentes reutilizables y la lógica crítica requieren pruebas. Las
  páginas principales requieren al menos una prueba de integración del flujo.

## Organización

- Importar módulos públicos a través de su `index.ts`; evitar dependencias entre
  internals de features distintas.
- Mantener los tipos de transporte separados de los modelos de vista.
- La comunicación con el servicio local se concentra en `src/lib/api`.
- Los textos visibles se centralizan para facilitar consistencia y futura
  internacionalización.
- Los archivos no deben crecer sin límite: dividirlos cuando mezclen más de una
  responsabilidad o sea difícil probarlos aisladamente.

## Documentación de la API

- La fuente de verdad de los endpoints es el esquema OpenAPI generado por
  FastAPI en `/openapi.json`.
- Para consulta interactiva usar `/docs` (Swagger UI) o `/redoc` con el backend
  en ejecución.
- Antes de crear, modificar o consumir un endpoint, revisar
  `backend/app/api/app.py`, `backend/app/api/schemas.py` y el OpenAPI generado.
- Las instrucciones de ejecución y operación viven en
  `docs/BACKEND_RUNBOOK.md`. Las decisiones y el avance del backend viven en
  `docs/BACKEND_DEVELOPMENT_PLAN.md` y
  `docs/BACKEND_IMPLEMENTATION_STATUS.md`.
- No documentar manualmente contratos que contradigan OpenAPI. Cuando cambie un
  endpoint, actualizar sus esquemas, pruebas y cualquier guía Markdown afectada
  dentro del mismo cambio.
- El frontend sólo puede consumir rutas documentadas bajo `/api/v1`; no debe
  inferir campos, estados ni códigos de error no declarados por el backend.

## Calidad y cambios

- Preservar evidencia, valores originales y valores normalizados.
- Un dato ausente nunca se convierte en cero ni en `false`.
- Ejecutar pruebas relevantes y validaciones estáticas antes de entregar.
- Instalar nuevas skills de agente sólo cuando el usuario lo solicite
  explícitamente. Una petición de diseño, desarrollo o recomendación no autoriza
  instalaciones. Instalar únicamente las skills solicitadas, preferentemente
  en la carpeta personal de Codex, sin agregar otras skills ni herramientas
  opcionales como parte de la instalación.
- No agregar dependencias del proyecto sin justificar su necesidad y registrarlas
  mediante el administrador de paquetes correspondiente.

## Planeación y diseño UX/UI con skills

- Antes de diseñar o modificar UI, leer `PRODUCT.md`, `DESIGN.md` y
  `docs/FINESSE_DESIGN_REFERENCE.md`. Finesse UI 1.0 es la referencia visual
  elegida por el usuario; su extracción es parcial y no autoriza una migración
  automática. Distinguir reglas observadas, adaptaciones del proyecto y valores
  pendientes de inspección. No inventar tokens de Figma ni sustituir los tokens
  actuales por estimaciones de capturas.

- Usar Impeccable y UI UX Pro Max en tareas de planeación, diseño, revisión o
  mejora de interfaces según el alcance. Leer su `SKILL.md` y sólo las referencias
  necesarias. No aplicarlas a cambios exclusivamente de backend.
- Las instrucciones explícitas del usuario y estas reglas prevalecen sobre
  recomendaciones de las skills. No ampliar el alcance por una recomendación.
- Antes de un rediseño, revisar la interfaz y los componentes existentes;
  identificar usuario, tarea principal, orden del flujo, información necesaria
  y problemas observables. Preguntar sólo por datos que cambien la propuesta.
- Impeccable guía el análisis del flujo, arquitectura de información, jerarquía,
  textos y crítica de la interfaz; también refina la propuesta implementada.
- UI UX Pro Max aporta consultas de patrones, accesibilidad, tipografía, color,
  densidad y recomendaciones para React, Tailwind y shadcn/ui. Adaptar los
  resultados al producto y verificar su pertinencia antes de adoptarlos.
- Mantener una sola propuesta y un solo sistema visual: consultar primero el
  contexto del producto y el diseño existente, luego las recomendaciones
  necesarias y finalmente revisar con Impeccable. Resolver contradicciones
  priorizando la tarea del usuario, accesibilidad y consistencia existente.
- Durante planeación, entregar flujos, organización o prototipos según lo
  solicitado; no modificar la UI hasta que el usuario pida implementar.
- Registrar contexto del producto en `PRODUCT.md` y decisiones visuales en
  `DESIGN.md` cuando el alcance requiera documentación de diseño. Reutilizar los
  archivos existentes; no generar otro sistema de diseño paralelo ni persistir
  propuestas automáticas sin revisar. Distinguir supuestos de decisiones acordadas.
- Reutilizar los componentes y tokens existentes. Priorizar legibilidad,
  navegación por teclado y claridad de datos; añadir animaciones o recursos
  decorativos sólo si ayudan a la tarea o el usuario los solicita.
- Validar en navegador los cambios implementados: flujo principal, estados
  `loading`, `empty`, `success`, `needs_review` y `error`, foco, contraste, zoom
  y tamaños de pantalla relevantes. Ejecutar pruebas y validaciones estáticas
  acordes al cambio; declarar qué no pudo comprobarse.
- La instalación de las skills no autoriza activar hooks, instalar extensiones,
  añadir dependencias ni cambiar configuraciones ajenas al trabajo solicitado.
