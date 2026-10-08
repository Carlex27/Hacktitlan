param(
    [ValidateSet("cpu", "cuda118", "cuda126", "cuda129")]
    [string]$Backend = "cpu",
    [ValidateSet("install", "repair", "verify", "remove", "status")]
    [string]$Action = "install",
    [switch]$SkipModelDownload,
    [string]$ModelRoot = "C:\ProgramData\Hacktitlan\models"
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) {
    throw "No existe el entorno Python del proyecto: $python"
}

function Invoke-CheckedNative {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments)
    & $Arguments[0] $Arguments[1..($Arguments.Length - 1)]
    if ($LASTEXITCODE -ne 0) {
        throw "Falló el comando externo con código ${LASTEXITCODE}: $($Arguments -join ' ')"
    }
}

if ($Action -eq "status") {
    Invoke-CheckedNative $python -c "from backend.app.config import get_settings; from backend.app.infrastructure.ocr import probe_ocr_runtime; import json; print(json.dumps(probe_ocr_runtime(get_settings()).as_dict(), indent=2))"
    exit 0
}

if ($Action -eq "verify") {
    Invoke-CheckedNative $python -c "from backend.app.config import get_settings; from backend.app.infrastructure.ocr.models import OcrModelManager; m = OcrModelManager('$ModelRoot'); ok, errs = m.verify(); print('Valid:', ok); print('Errors:', errs); exit(0 if ok else 1)"
    exit 0
}

if ($Action -eq "remove") {
    Invoke-CheckedNative $python -c "from backend.app.infrastructure.ocr.models import OcrModelManager; m = OcrModelManager('$ModelRoot'); print('Removed:', m.remove_package())"
    Write-Host "Desinstalando paquetes Python OCR opcionales..."
    & uv pip uninstall --python $python paddlepaddle paddlepaddle-gpu paddleocr paddlex
    Write-Host "Componente OCR eliminado correctamente."
    exit 0
}

if ($Action -eq "repair") {
    Invoke-CheckedNative $python -c "from backend.app.infrastructure.ocr.models import OcrModelManager; m = OcrModelManager('$ModelRoot'); s = m.repair_package(); print('Repaired status:', s.status)"
    exit 0
}

# Action: install
# OCR remains an optional hardware-specific component. It is intentionally not
# part of the base uv.lock because CPU and GPU Paddle wheels are mutually exclusive.
Invoke-CheckedNative uv pip install --python $python "paddleocr==3.7.0" "paddlex[ocr]==3.7.2"
if ($Backend -eq "cpu") {
    Invoke-CheckedNative uv pip install --python $python "paddlepaddle==3.3.0" `
        --index-url "https://www.paddlepaddle.org.cn/packages/stable/cpu/"
} else {
    $cudaDirectory = $Backend.Replace("cuda", "cu")
    $wheel = "https://paddle-whl.cdn.bcebos.com/stable/$cudaDirectory/paddlepaddle-gpu/" +
        "paddlepaddle_gpu-3.3.0-cp312-cp312-win_amd64.whl"
    Invoke-CheckedNative uv pip install --python $python $wheel
}

Invoke-CheckedNative $python -c "import paddle; paddle.utils.run_check()"

if (-not $SkipModelDownload) {
    Invoke-CheckedNative $python -c "from backend.app.infrastructure.ocr.models import OcrModelManager; m = OcrModelManager('$ModelRoot'); has_space, free_b, req_b = m.check_disk_space(); print(f'Espacio libre: {free_b // (1024*1024)} MB, requerido: {req_b // (1024*1024)} MB');"
    Invoke-CheckedNative $python -c "from paddleocr import PPStructureV3; PPStructureV3(use_doc_orientation_classify=True, use_doc_unwarping=False, use_table_recognition=True, use_formula_recognition=False, use_chart_recognition=False)"
}

Write-Host "OCR local instalado. Configure HACKTITLAN_OCR_ENABLED=true."
