export type ProcessingStatus =
  | "loading"
  | "empty"
  | "success"
  | "needs_review"
  | "error";

export interface ChemicalObservation {
  element: string;
  rawValue: string | null;
  percentage: number | null;
  page: number;
}

export interface CertificateProductSummary {
  productId: string;
  heatNumber: string | null;
  status: ProcessingStatus;
  composition: readonly ChemicalObservation[];
}
