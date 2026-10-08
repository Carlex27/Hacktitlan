# Empaquetado

Configuración futura de PyInstaller para el sidecar y de Tauri Bundler para el
instalador de Windows.

## Componente OCR opcional

El instalador puede invocar `scripts/install-ocr-runtime.ps1` después de la
comprobación de hardware. Los perfiles disponibles son `cpu`, `cuda118`,
`cuda126` y `cuda129`. El script usa `uv`, fija PaddleOCR 3.7.0 y PaddlePaddle
3.3.0, instala los extras OCR de PaddleX 3.7.2, valida el runtime y descarga
PP-StructureV3 salvo que se use
`-SkipModelDownload`.

CPU:

```powershell
.\scripts\install-ocr-runtime.ps1 -Backend cpu
```

NVIDIA con runtime CUDA 12.6:

```powershell
.\scripts\install-ocr-runtime.ps1 -Backend cuda126
```

CPU y GPU son componentes mutuamente excluyentes. La aplicación base continúa
funcionando sin ellos y conserva los documentos escaneados como `needs_ocr`.
