/**
 * Tipos de transporte del API v1. Reflejan exactamente las respuestas del
 * backend (snake_case); los modelos de vista viven en cada feature.
 */
export type { ActorReasonDto, JsonObject, JsonValue } from "./common";
export type {
  ApprovalStatusDto,
  CandidateSelectionDto,
  CandidateSelectionRequestDto,
  CandidateSupportLevelDto,
  ClassificationCandidateDto,
  ClassificationOutcomeDto,
  ClassificationResultDto,
  ClassificationRunDto,
  ClassificationRunSummaryDto,
  ClassificationSelectionDto,
  DecisionStepDto,
  DecisionStepOutcomeDto,
  EvidenceLinkDto,
  EvidenceSourceTypeDto,
} from "./classification";
export type { JobDto, JobStatusDto, UploadDocumentDto } from "./documents";
export type {
  EvidenceDetailDto,
  ObservationEvidenceDto,
  RuleSourceEvidenceDto,
} from "./evidence";
export type { HealthLiveDto, HealthReadyDto } from "./health";
export type {
  GpuDeviceDto,
  HardwareCompatibilityDto,
  HardwareProfileDto,
  OcrStatusDto,
} from "./ocr";
