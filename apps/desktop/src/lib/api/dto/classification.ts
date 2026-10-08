import type { ActorReasonDto, JsonObject, JsonValue } from "./common";

export type ApprovalStatusDto = "draft" | "needs_review" | "approved" | "rejected";

export type ClassificationOutcomeDto = "classified" | "needs_review" | "out_of_scope";

export type DecisionStepOutcomeDto = "matched" | "not_matched" | "missing" | "ambiguous";

export type CandidateSupportLevelDto = "fully_supported" | "conditional";

export type EvidenceSourceTypeDto = "observation" | "rule_source";

/** `GET /api/v1/certificates/{id}/classification-runs` (más reciente primero). */
export interface ClassificationRunSummaryDto {
  id: number;
  rule_set_id: number;
  parent_run_id: number | null;
  approval_status: ApprovalStatusDto;
  demo_notice: string;
  created_at: string;
}

export interface ClassificationCandidateDto {
  id: number;
  rank: number;
  fraction: string;
  nico: string;
  description: string | null;
  support_level: CandidateSupportLevelDto;
  details: JsonObject;
}

export interface ClassificationSelectionDto {
  id: number;
  candidate_id: number;
  supersedes_selection_id: number | null;
  person_name: string;
  reason: string;
  workstation_name: string;
  created_at: string;
}

export interface EvidenceLinkDto {
  id: number;
  source_type: EvidenceSourceTypeDto;
  field_path: string | null;
  observation_id: number | null;
  reference: JsonObject;
  /** Ruta relativa al API; resolver con `ApiClient.url()`. */
  detail_url: string;
}

export interface DecisionStepDto {
  id: number;
  sequence: number;
  rule_code: string;
  /** Valores conocidos en `DecisionStepOutcomeDto`; el backend admite otros. */
  outcome: DecisionStepOutcomeDto | (string & {});
  inputs: JsonObject;
  evidence: readonly JsonValue[];
  evidence_links: readonly EvidenceLinkDto[];
  explanation: string | null;
}

export interface ClassificationResultDto {
  id: number;
  product_id: number;
  product_type: string | null;
  fraction: string | null;
  nico: string | null;
  description: string | null;
  outcome: ClassificationOutcomeDto;
  details: JsonObject;
  /** Ordenados por `rank`. */
  candidates: readonly ClassificationCandidateDto[];
  /** Historial inmutable; la última selección reemplaza a las anteriores. */
  selections: readonly ClassificationSelectionDto[];
  steps: readonly DecisionStepDto[];
}

/** `GET /api/v1/classification-runs/{id}`. */
export interface ClassificationRunDto {
  id: number;
  certificate_id: number;
  rule_set_id: number;
  parent_run_id: number | null;
  approval_status: ApprovalStatusDto;
  input_snapshot: JsonObject;
  demo_notice: string;
  results: readonly ClassificationResultDto[];
}

/** Cuerpo de `POST /api/v1/classification-results/{id}/select`. */
export interface CandidateSelectionRequestDto extends ActorReasonDto {
  candidate_id: number;
}

export interface CandidateSelectionDto {
  selection_id: number;
  classification_result_id: number;
  candidate_id: number;
  fraction: string;
  nico: string;
  person_name: string;
  reason: string;
  workstation_name: string;
  created_at: string;
}

/** Respuesta de `POST /api/v1/classification-runs/{id}/approve` y `reject` */
export interface RunApprovalResultDto {
  classification_run_id: number;
  approval_status: ApprovalStatusDto;
}

