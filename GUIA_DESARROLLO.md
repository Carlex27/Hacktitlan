# Guía de Inicio Rápido y Entorno de Pruebas (Backend + Frontend)

Esta guía explica cómo levantar y probar el backend de Hacktitlan en **modo desarrollo** sin necesidad de empaquetar la aplicación de escritorio, así como las opciones para conectar el frontend React (`apps/desktop`) con la API local.

---

## 1. Requisitos Previos

1. **Python 3.12+** administrado con `uv`.
2. **PostgreSQL 18** en ejecución local (puerto `5432`).
3. Base de datos creada (`hackaitlac` según tu `.env`).
4. Repositorio sincronizado:
   ```powershell
   uv sync --all-groups
   ```

---

## 2. Verificación de Base de Datos y Migraciones

Antes de iniciar el backend por primera vez, confirma que las migraciones de Alembic estén al día:

```powershell
# Verificar revisión actual
uv run alembic current

# Si hace falta actualizar a la última revisión:
uv run alembic upgrade head
```

*(La revisión actual del esquema es `0006_rule_set_immutability (head)`).*

---

## 3. Comandos para Iniciar el Backend

El backend se compone de dos procesos que deben correr en **terminales independientes**:

### Terminal 1: Servidor de API (FastAPI / Uvicorn)

Inicia el servidor HTTP con recarga en caliente (`--reload`):

```powershell
uv run uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8765
```

> **Alternativa mediante script:**
> ```powershell
> .\scripts\run-api.ps1
> ```

Una vez iniciado, valida que responda:
- **Salud del sistema:** [http://127.0.0.1:8765/api/v1/health/ready](http://127.0.0.1:8765/api/v1/health/ready)
- **Documentación Swagger UI interactiva:** [http://127.0.0.1:8765/docs](http://127.0.0.1:8765/docs)
- **Documentación ReDoc:** [http://127.0.0.1:8765/redoc](http://127.0.0.1:8765/redoc)
- **Esquema OpenAPI en JSON:** [http://127.0.0.1:8765/openapi.json](http://127.0.0.1:8765/openapi.json)

---

### Terminal 2: Worker en Segundo Plano

El worker procesa la cola de tareas asíncronas: ingestión de PDFs, extracción, OCR (PP-StructureV3), reclasificación y generación de archivos Excel:

```powershell
uv run python -m backend.app.application.worker
```

> **Alternativa mediante script:**
> ```powershell
> .\scripts\run-worker.ps1
> ```

---

## 4. Conexión del Frontend con el Backend en Entorno de Desarrollo

El frontend (`apps/desktop/src`) es una SPA en React + TypeScript. En modo desarrollo no requiere el binario de Tauri para probarse; se puede ejecutar directamente en el navegador con Vite.

### 4.1. Configuración de CORS en el Backend
El backend ya cuenta con `CORSMiddleware` activo, admitiendo peticiones desde cualquier origen local (`http://localhost:5173`, `http://127.0.0.1:5173`, `tauri://localhost`, etc.).

### 4.2. Estrategias de Conexión Frontend -> Backend

Hay dos formas principales de configurar la comunicación:

#### Opción A: Variable de Entorno (`VITE_API_URL`) — Recomendada para consumo directo
En `apps/desktop/.env` (o `.env.development`):
```env
VITE_API_BASE_URL=http://127.0.0.1:8765/api/v1
```
En el cliente HTTP de `apps/desktop/src/lib/api`:
```typescript
const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8765/api/v1';

export async function fetchCertificates() {
  const response = await fetch(`${BASE_URL}/certificates`);
  return response.json();
}
```

#### Opción B: Proxy Inverso en Vite (`vite.config.ts`) — Recomendada para evitar URLs absolutas
Permite que el frontend haga peticiones relativas (`/api/v1/...`) y Vite las reenvíe automáticamente al backend en el puerto 8765:

```typescript
// apps/desktop/vite.config.ts
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8765',
        changeOrigin: true,
      },
    },
  },
});
```

De esta forma, en el código del frontend se invoca directamente:
```typescript
const response = await fetch('/api/v1/certificates');
```

---

## 5. Contrato de API y Reglas de Desarrollo

De acuerdo con [`AGENTS.md`](./AGENTS.md):

1. **Estructura uniforme de respuesta:**
   Todas las respuestas exitosas devuelven:
   ```json
   {
     "data": { ... },
     "meta": { ... },
     "error": null
   }
   ```
   En caso de error (4xx / 5xx):
   ```json
   {
     "data": null,
     "meta": {},
     "error": {
       "code": "codigo_error_estable",
       "message": "Descripción clara del error",
       "details": { ... }
     }
   }
   ```
2. **Centralización del cliente:**
   Toda llamada al backend debe vivir dentro de `apps/desktop/src/lib/api/`. Los componentes de React en `features/` consumen estos métodos mediante hooks y no deben contener llamadas `fetch` directas en el JSX.
3. **Manejo de estados en la UI:**
   Cada vista o componente debe contemplar explícitamente los estados: `loading`, `empty`, `success`, `needs_review` y `error`.

---

## 6. Ciclo de Prueba Manual Básico

Puedes probar el flujo completo desde **Swagger UI** (`http://127.0.0.1:8765/docs`):

1. **Subir un certificado:**
   `POST /api/v1/documents` adjuntando un archivo PDF de prueba. Recibirás un `document_id` y `job_id` con estado `202 Accepted`.
2. **Verificar procesamiento del Worker:**
   Observa la Terminal 2: el worker tomará el trabajo, extraerá datos y registrará el certificado en la base de datos.
3. **Consultar actas y filtros:**
   `GET /api/v1/certificates?period=today` para verificar el acta creada y sus coladas.
4. **Ver candidatos de clasificación y factores:**
   `GET /api/v1/classification-runs/{run_id}` para inspeccionar las alternativas arancelarias evaluadas y sus reglas.
5. **Seleccionar candidato:**
   `POST /api/v1/classification-results/{result_id}/select` con `person_name`, `reason` y el `candidate_id` elegido.
6. **Exportar a Excel auditable de 8 hojas:**
   `POST /api/v1/exports` solicitando la exportación del acta, y posteriormente descargar el `.xlsx` generado.

---

## 7. Ejecutar Pruebas Automatizadas

Para validar que todo el código del backend, motor arancelario y reportes sigan funcionando al 100%:

```powershell
uv run pytest
```
*(Se ejecutan más de 190 pruebas automáticas en pocos segundos).*
