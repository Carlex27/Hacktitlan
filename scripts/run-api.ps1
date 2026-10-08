$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
$apiHost = if ($env:HACKTITLAN_API_HOST) { $env:HACKTITLAN_API_HOST } else { "127.0.0.1" }
$apiPort = if ($env:HACKTITLAN_API_PORT) { $env:HACKTITLAN_API_PORT } else { "8765" }
uv run uvicorn backend.app.main:app --host $apiHost --port $apiPort

