# Editor y activación de formatos — 2026-10-09

## Entrega

Biblioteca web con creación de borradores, versiones, búsqueda y documentos de
ejemplo. El editor muestra páginas preparadas, permite seleccionar regiones con
arrastre, bloques accesibles por teclado o porcentajes, y configurar campos,
textos de reconocimiento y columnas de tablas. Reutiliza componentes y tokens
existentes; no añade dependencias.

Las pruebas muestran valores originales y normalizados, unidades, página,
evidencia y diagnósticos. La confirmación exige revisar el layout exacto de la
prueba. Guardar cambios invalida pruebas anteriores. Los errores conservan el
borrador local y las operaciones muestran progreso/cancelación.

La activación requiere dos textos estables distintos y tres documentos distintos
con pruebas satisfactorias confirmadas de la misma revisión y extractor.
Activar una versión retira atómicamente la anterior. Versiones activas/retiradas
son inmutables; persona, motivo y evidencia mínima de validación quedan auditados.

API y worker fijan candidatos antes de encolar. Los adaptadores calibrados
conservan prioridad; coincidencias ambiguas requieren revisión. Reprocesar con
una plantilla explícita crea otra revisión sin sobrescribir la original. La
extracción por plantilla siempre requiere revisión documental posterior.

Los contratos se consultan en OpenAPI; operación y despliegue en
[`BACKEND_RUNBOOK.md`](../BACKEND_RUNBOOK.md). También se corrigió una carrera de
transacciones: la sesión confirma antes de enviar la respuesta HTTP, evitando
404 al consultar inmediatamente un trabajo recién creado.

## Validación

- Backend: 67 pruebas relevantes pasan (reconocimiento, regiones, imágenes,
  biblioteca, activación y contrato PostgreSQL).
- Suite backend completa: 600 pasan, una falla preexistente en
  `test_molino3_conflicting_ocr_proposal_can_be_accepted_with_audit`, y una omitida
  de respaldo/restauración por requisitos externos.
- Frontend: 193 pruebas en 46 archivos pasan; las cinco pruebas del editor y
  geometría se repitieron tras los últimos ajustes. TypeScript, ESLint y build
  pasan.
- Navegador: selección por teclado, guardar, probar, confirmar, activar;
  estados de carga y error/reintento, pantallas de 1400 y 390 px, y zoom 200%.
- HTTP real con API/worker y base exclusiva de QA: tres PDFs digitales con
  valores distintos permitieron activar la versión. Un cuarto documento produjo
  automáticamente R4 y espesor 1.4 mm mediante `user_template`.
- Reprocesamiento desde el navegador terminado: abrió una nueva acta #5 con
  H3, R3 y espesor 1.3 mm; la revisión original se conserva.
- La migración 0011 se aplicó en `hacktitlan_test`. La base habitual no cambió.

Evidencia local de esta sesión: `format-editor-wide.jpg`,
`format-editor-mobile.jpg`, `format-editor-completed.jpg` y
`format-qa-isolated-result.json`, en
`C:/Users/ofici/.codex/visualizations/2026/10/09/01a11fdd-0ec2-7972-8710-429a023fe0dc`.

## Despliegue y límites

Actualización posterior: la base habitual `hackaitlac` ya quedó en
`0011_format_activation`. Se verificaron las diferencias de metadatos, claves
foráneas y el trigger de inmutabilidad antes de recuperar el historial vacío.
Se aplicaron 0009, 0010 y 0011 y se registró la revisión en una sola transacción.
Los conteos de todas las tablas existentes permanecieron iguales. La API devuelve
200 en `/api/v1/certificate-formats` y el navegador carga los PDFs disponibles
sin el error de conexión. Evidencia: `FORMAT_LIBRARY_DATABASE_DEPLOYMENT.json`.
La advertencia de despliegue siguiente describe el estado anterior a esta
corrección, y sigue siendo aplicable a otras bases con historial vacío.

No basta reiniciar los procesos: falta aplicar las migraciones a la base
habitual. Se encontraron tablas existentes con `alembic_version` vacío; primero
hay que identificar y reconciliar su revisión de origen, sin ejecutar migraciones
a ciegas ni usar `stamp head` para saltarlas. Después migrar y reiniciar API,
worker y frontend.

Esta entrega cubre regiones y tablas simples detectadas. No valida todavía el
flujo completo con tablas complejas multipágina de los certificados escaneados
del piloto original. Tres ejemplos no garantizan generalización a otros diseños.
La atribución de persona conserva el modelo local existente y no constituye
autenticación; la API debe permanecer en loopback.
