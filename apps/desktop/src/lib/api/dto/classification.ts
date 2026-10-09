import type { ActorReasonDto, JsonObject, JsonValue } from "./common";

export type ApprovalStatusDto = "draft" | "needs_review" | "approved" | "rejected";

export type ClassificationOutcomeDto = "classified" | "needs_review" | "out_of_scope";

export type DecisionStepOutcomeDto = "matched" | "not_matched" | "missing" | "ambiguous";

export type CandidateSupportLevelDto = "fully_supported" | "conditional";

export type EvidenceSourceTypeDto = "observation" | "rule_source";

export type CandidateFactorOutcomeDto =
  | "matched"
  | "not_matched"
  | "missing"
  | "ambiguous"
  | "unknown"
  | "conflict";

/** `GET /api/v1/certificates/{id}/classification-runs` (más reciente primero). */
export interface ClassificationRunSummaryDto {
  id: number;
  rule_set_id: number;
  parent_run_id: number | null;
  approval_status: ApprovalStatusDto;
  demo_notice: string;
  created_at: string;
}

/** Condición evaluada para sostener un candidato (valor esperado vs observado). */
export interface CandidateFactorDto {
  id: number;
  sequence: number;
  rule_code: string;
  outcome: CandidateFactorOutcomeDto;
  operator: string | null;
  expected: JsonObject;
  observed: JsonObject;
  unit: string | null;
  explanation: string;
  /** Si es `true`, el candidato no debe elegirse mientras el factor no se cumpla. */
  required_for_selection: boolean;
  evidence_links: readonly EvidenceLinkDto[];
}

export interface ClassificationCandidateDto {
  id: number;
  rank: number;
  fraction: string;
  nico: string;
  description: string | null;
  support_level: CandidateSupportLevelDto;
  details: JsonObject;
  /** Ruta relativa al detalle del candidato; resolver con `ApiClient.url()`. */
  detail_url: string;
  /** Ordenados por `sequence`. */
  factors: readonly CandidateFactorDto[];
}

/** `GET /api/v1/classification-candidates/{id}`. */
export interface ClassificationCandidateDetailDto
  extends Omit<ClassificationCandidateDto, "detail_url"> {
  classification_result_id: number;
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
  /** Selección vigente según el backend (considera reemplazos); `null` si no hay. */
  current_selection: ClassificationSelectionDto | null;
  /** Historial inmutable de selecciones. */
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

