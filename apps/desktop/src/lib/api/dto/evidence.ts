import type { JsonObject, JsonValue } from "./common";

/** Evidencia que proviene de la fuente de reglas (LIGIE), no del PDF. */
export interface RuleSourceEvidenceDto {
  id: number;
  /** Paso de decisión o factor de candidato al que respalda (uno de los dos). */
  decision_step_id: number | null;
  candidate_factor_id: number | null;
  source_type: "rule_source";
  reference: JsonObject;
}

/** Evidencia que apunta a una observación extraída del acta. */
export interface ObservationEvidenceDto {
  id: number;
  decision_step_id: number | null;
  candidate_factor_id: number | null;
  source_type: "observation";
  field_path: string | null;
  observation: {
    id: number;
    raw_value: JsonValue;
    normalized_value: JsonValue;
    unit: string | null;
    confidence: number | null;
    source_text: string | null;
  };
  document: {
    id: number;
    /** Ruta relativa al API; resolver con `ApiClient.url()`. */
    file_url: string;
  };
  focus: {
    page_number: number | null;
    bbox: JsonValue;
    can_focus_region: boolean;
    /** `full_page` cuando no hay página y región para enfocar. */
    fallback: "full_page" | null;
  };
}

/** `GET /api/v1/evidence/{id}`; distinguir por `source_type`. */
export type EvidenceDetailDto = RuleSourceEvidenceDto | ObservationEvidenceDto;
