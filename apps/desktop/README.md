# Aplicación de escritorio

La revisión documental usa `DocumentReviewList` y la cola `/api/v1/document-reviews`.
`App` acepta `apiBaseUrl` para configurar el host del backend; por defecto usa
el origen del navegador y requiere proxy `/api/v1`. Para conexión directa pasar
`http://100.74.94.9:8765` desde el punto de entrada del frontend y configurar CORS
para el origen autorizado. La lista permite actualizar estados y bloquea el botón
mientras exista un trabajo activo o una solicitud de reprocesamiento pendiente.

Frontend React + TypeScript y shell Tauri. La carpeta está preparada sin
dependencias instaladas; los manifiestos y el toolchain se agregarán cuando se
inicie la fase de implementación de la aplicación.

## Estructura

- `src/app`: composición raíz, rutas y proveedores.
- `src/pages`: páginas delgadas que componen features.
- `src/features`: módulos verticales del dominio.
- `src/components/ui`: componentes visuales reutilizables y sin reglas de negocio.
- `src/lib`: adaptadores compartidos, API local y utilidades.
- `src/types`: tipos compartidos del frontend.
- `src/styles`: tokens y estilos globales.
- `tests`: pruebas unitarias, de integración y end-to-end.
- `src-tauri`: shell nativo, permisos y configuración de Tauri.

Las reglas obligatorias de componentes están en el `AGENTS.md` de la raíz.
