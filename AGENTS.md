# Reglas de desarrollo del repositorio

Estas reglas aplican a todo el proyecto.

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
- No instalar nuevas skills de agente para trabajar en este repositorio. No
  agregar dependencias del proyecto sin justificar su necesidad y registrarlas
  mediante el administrador de paquetes correspondiente.
