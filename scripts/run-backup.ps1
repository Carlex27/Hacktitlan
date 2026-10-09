$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
uv run python -m backend.app.operations.backup
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
