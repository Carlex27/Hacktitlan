param(
    [ValidateSet("cpu", "cuda118", "cuda126", "cuda129")]
    [string]$Backend = "cpu",
    [switch]$SkipModelDownload
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
    Invoke-CheckedNative $python -c "from paddleocr import PPStructureV3; PPStructureV3(use_doc_orientation_classify=True, use_doc_unwarping=False, use_table_recognition=True, use_formula_recognition=False, use_chart_recognition=False)"
}

Write-Host "OCR local instalado. Configure HACKTITLAN_OCR_ENABLED=true."
