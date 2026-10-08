# Operación local del backend

## Requisitos del servidor

- Windows 11 x64, Python 3.12–3.14 y `uv`.
- PostgreSQL 18 nativo, incluyendo `psql`, `pg_dump` y `pg_restore` en `PATH`.
- Tailscale conectado. PostgreSQL permanece en loopback; sólo la API escucha en
  la IP Tailscale del servidor.

## Preparación

1. Cambiar las contraseñas de ejemplo en `scripts/postgres/bootstrap.sql` y
   ejecutarlo con `psql -U postgres -f scripts/postgres/bootstrap.sql`.
2. Ejecutar `uv sync --all-groups` y copiar `.env.example` a `.env`.
3. Usar temporalmente la cuenta migradora en `HACKTITLAN_DATABASE_URL`, ejecutar
   `uv run alembic upgrade head` y después cambiar la URL a `hacktitlan_app`.
4. Configurar
   `HACKTITLAN_API_HOST` con la IP Tailscale y elegir una carpeta secundaria de
   respaldo distinta del disco principal.
5. Ejecutar `scripts/run-api.ps1` y `scripts/run-worker.ps1`.

El firewall de Windows debe admitir TCP al puerto configurado únicamente desde
la interfaz/perfil de Tailscale. PostgreSQL no debe publicarse en Tailscale ni
en Internet. El cliente consume sólo `http://<ip-tailscale>:8765/api/v1`.
Aplicar la regla como administrador con
`scripts/configure-tailscale-firewall.ps1 -TailscaleIPv4 <ip-tailscale>`.

## Validación

```powershell
uv run pytest
uv run alembic current
Invoke-RestMethod http://127.0.0.1:8765/api/v1/health/ready
```

Las pruebas de integración requieren una base migrada llamada exactamente
`hacktitlan_test` y la variable `HACKTITLAN_TEST_DATABASE_URL`. No apuntar estas
pruebas a producción.

## Respaldo y restauración

Ejecutar `scripts/install-backup-task.ps1` como administrador una vez. La tarea
corre a las 02:00 y `StartWhenAvailable` recupera una ejecución perdida. Conserva
7 respaldos diarios, 4 semanales y 12 mensuales, verifica el dump mediante
`pg_restore --list`, incluye archivos y reglas, y valida el hash de la segunda
copia.

Una exportación integral manual se genera con
`uv run python -m backend.app.operations.backup --kind manual`.

La restauración es deliberadamente local y manual. En una base vacía:

1. Extraer el ZIP y comprobar los hashes de `manifest.json`.
2. Ejecutar `pg_restore --list database.dump`.
3. Restaurar con una cuenta administradora:
   `pg_restore --clean --if-exists --no-owner --dbname hacktitlan database.dump`.
4. Copiar `storage/` a la ruta configurada y validar `/health/ready`.

No existe endpoint remoto de restauración.
