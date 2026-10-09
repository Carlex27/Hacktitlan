param([Parameter(Mandatory = $true)][string]$DatabaseName)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location -LiteralPath $projectRoot
try {
    uv run python -m backend.app.operations.reset_database --confirm-database $DatabaseName
    if ($LASTEXITCODE -ne 0) { throw "No se reinició la base de datos (código $LASTEXITCODE)." }
} finally {
    Pop-Location
}
