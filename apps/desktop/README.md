# Aplicación de escritorio

Frontend React 19 + TypeScript + Vite, UI con shadcn/ui (Radix, Tailwind v4) y
shell Tauri 2. Las reglas obligatorias de componentes están en el `AGENTS.md` de
la raíz.

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

La app consume el API v1 del backend central; no accede a PostgreSQL. La URL se
configura con `VITE_API_BASE_URL` (ver `.env.example`; por defecto
`http://127.0.0.1:8765`). Para el segundo equipo use el nombre MagicDNS de
Tailscale, p. ej. `http://servidor.tailnet.ts.net:8765`.

Si cambia el host, actualice también:

- `connect-src` de la CSP en `src-tauri/tauri.conf.json` (permite `127.0.0.1`,
  `localhost` y `*.ts.net` en el puerto 8765).
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
