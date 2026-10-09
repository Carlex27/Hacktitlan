/** `GET /api/v1/ocr/status`: disponibilidad del paquete opcional de OCR. */

export type HardwareCompatibilityDto =
  | "supported"
  | "supported_with_limits"
  | "unsupported"
  | "unknown";

export interface GpuDeviceDto {
  vendor: string;
  name: string;
  memory_mb: number | null;
  driver_version: string | null;
  compute_capability: string | null;
}

export interface HardwareProfileDto {
  architecture: string;
  operating_system: string;
  total_memory_mb: number | null;
  available_memory_mb: number | null;
  gpus: readonly GpuDeviceDto[];
  compatibility: HardwareCompatibilityDto;
  reasons: readonly string[];
}

export type OcrModelPackageStateDto = "installed" | "not_installed" | "downloading" | "corrupted";

/** `GET /api/v1/ocr/models` y campo `models` de `OcrStatusDto`. */
export interface OcrModelPackageStatusDto {
  name: string;
  version: string;
  status: OcrModelPackageStateDto;
  installed_files: number;
  total_files: number;
  installed_bytes: number;
  total_bytes: number;
  backend: string;
  message: string;
}

/** `POST /api/v1/ocr/smoke-check`. */
export interface OcrSmokeCheckDto {
  success: boolean;
  requested_device: string;
  effective_device: string | null;
  elapsed_ms: number;
  paddle_version: string | null;
  paddleocr_version: string | null;
  message: string;
}

export interface OcrStatusDto {
  enabled: boolean;
  installed: boolean;
  healthy: boolean;
  compatibility: HardwareCompatibilityDto;
  selected_device: string | null;
  paddle_version: string | null;
  paddleocr_version: string | null;
  hardware: HardwareProfileDto;
  message: string;
  models: OcrModelPackageStatusDto | null;
}
