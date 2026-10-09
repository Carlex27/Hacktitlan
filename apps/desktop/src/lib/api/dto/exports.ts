import type { JsonObject } from "./common";

/** Cuerpo de `POST /api/v1/exports`; requiere al menos un alcance no vacío. */
export interface ExportRequestDto {
  certificate_ids?: readonly number[];
  heat_ids?: readonly number[];
  classification_run_ids?: readonly number[];
  filters?: JsonObject;
  /** Un reporte oficial sólo admite actas y ejecuciones aprobadas (409 si no). */
  official?: boolean;
  person_name: string;
  workstation_name?: string | null;
}

export interface ExportCreatedDto {
  export_id: number;
  job_id: number;
}

export type ExportStateDto = "queued" | "running" | "succeeded" | "failed";

/** `GET /api/v1/exports/{id}`. */
export interface ExportStatusDto {
  id: number;
  format: string;
  status: ExportStateDto;
  scope: JsonObject;
  filters: JsonObject;
  person_name: string;
  workstation_name: string;
  sha256: string | null;
  stored_file_id: number | null;
  error_message: string | null;
  created_at: string;
  /** Ruta relativa disponible sólo cuando `status` es `succeeded`. */
  download_url: string | null;
}
