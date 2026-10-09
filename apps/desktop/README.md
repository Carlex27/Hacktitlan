# Aplicación de escritorio

# Aplicación de escritorio

Frontend React 19 + TypeScript + Vite, UI con shadcn/ui (Radix, Tailwind v4) y shell Tauri 2. Las reglas obligatorias de componentes están en el `AGENTS.md` de la raíz.

La importación permite seleccionar PDF/XLSX y enviarlos mediante multipart a `/api/v1/documents`, usando el mismo `apiBaseUrl` configurado en `App`. Conserva los recibos de los archivos enviados si falla uno del lote; volver a enviar usa la deduplicación del backend. Cada recibo muestra una barra de progreso consultando su trabajo cada segundo. La subida y la espera de la primera respuesta usan una barra indeterminada. El porcentaje posterior pertenece al procesamiento, no a los bytes transferidos ni al tiempo restante. La consulta se detiene al terminar el trabajo; revisión, falta de OCR, fallo y cancelación se muestran explícitamente. Si falla la conexión, se puede reintentar la consulta sin volver a subir el archivo. Los datos se consultan actualizando la cola de revisión. No incluye todavía un visor de Excel.

La revisión documental usa `DocumentReviewList` y la cola `/api/v1/document-reviews`.
`App` acepta `apiBaseUrl` para configurar el host del backend; por defecto usa el origen del navegador y requiere proxy `/api/v1`. Para conexión directa pasar `http://100.74.94.9:8765` desde el punto de entrada del frontend y configurar CORS para el origen autorizado. La lista permite actualizar estados y bloquea el botón mientras exista un trabajo activo o una solicitud de reprocesamiento pendiente.

## Requisitos

- Node 24 y pnpm 11
- Rust estable (MSVC) y WebView2 (incluido en Windows 11)

## Comandos

```powershell
pnpm install          # dependencias
pnpm tauri dev        # ventana de escritorio con recarga en caliente
pnpm dev              # sólo la interfaz en http://localhost:1420
pnpm test             # Vitest (unitarias + integración)
pnpm typecheck        # TypeScript estricto
pnpm lint             # ESLint
pnpm tauri build      # instaladores NSIS/MSI en src-tauri/target/release/bundle
```

## Servidor

La app consume el API v1 del backend central; no accede a PostgreSQL/Supabase
(sólo el backend tiene sus credenciales). La URL se configura con
`VITE_API_BASE_URL` en `apps/desktop/.env` (ver `.env.example`; por defecto
`http://127.0.0.1:8765`). El servidor de la demostración está en Tailscale:
`http://100.74.94.9:8765` (MagicDNS: `carlonsioz.taile215a8.ts.net`).

Si cambia el host, actualice también:

- `connect-src` de la CSP en `src-tauri/tauri.conf.json` (permite `127.0.0.1`,
  `localhost`, `100.74.94.9` y `*.ts.net` en el puerto 8765).
- `HACKTITLAN_CORS_ORIGINS` del backend si cambia el origen del webview.

Sin servidor la app queda bloqueada y muestra qué componente falla (backend
inalcanzable o PostgreSQL/almacenamiento no listos), con opción de reintentar.

## Estructura

- `src/app`: composición raíz y proveedores (cliente API inyectable).
- `src/pages`: páginas delgadas que componen features.
- `src/features`: módulos verticales (`connection-status`, `certificate-import`, …).
  Cada uno separa `model/` (funciones puras), `hooks/` y `components/`.
- `src/components/ui`: primitivas shadcn (`pnpm dlx shadcn@latest add <componente>`).
- `src/components/feedback`, `src/components/layout`: componentes genéricos propios.
- `src/lib/api`: único acceso al backend: cliente tipado, DTO, sobre
  `{ data, meta, error }`, `ApiError` y cancelación.
- `src/lib/i18n`: textos visibles centralizados.
- `src/types`: tipos compartidos del frontend.
- `tests/unit`, `tests/integration`, `tests/support` (backend simulado).
- `src-tauri`: shell nativo, capacidades mínimas (`core:default`) y empaquetado.
