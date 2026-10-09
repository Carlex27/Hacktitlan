import { useState } from "react";

import {
  selectClassificationCandidate,
  deselectClassificationCandidate,
  useApiClient,
  type ApiError,
  type CandidateSelectionDto,
  type CandidateSelectionRequestDto,
} from "@/lib/api";

export interface UseCandidateSelectionResult {
  selectCandidate(
    resultId: number,
    candidateId: number,
    personName: string,
    reason: string,
  ): Promise<CandidateSelectionDto>;
  selectManual(resultId: number, fraction: string, nico: string, personName: string, reason: string): Promise<CandidateSelectionDto>;
  deselect(resultId: number, personName: string, reason: string): Promise<void>;
  isSubmitting: boolean;
  error: ApiError | null;
  clearError(): void;
}

export function useCandidateSelection(): UseCandidateSelectionResult {
  const api = useApiClient();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);

  async function submit(resultId: number, request: CandidateSelectionRequestDto): Promise<CandidateSelectionDto> {
    setIsSubmitting(true);
    setError(null);
    try {
      const res = await selectClassificationCandidate(api, resultId, request);
      setIsSubmitting(false);
      return res;
    } catch (err) {
      setError(err as ApiError);
      setIsSubmitting(false);
      throw err;
    }
  }

  function clearError() {
    setError(null);
  }

  async function deselect(resultId: number, personName: string, reason: string) {
    setIsSubmitting(true);
    setError(null);
    try {
      await deselectClassificationCandidate(api, resultId, { person_name: personName, reason });
    } catch (err) {
      setError(err as ApiError);
      throw err;
    } finally {
      setIsSubmitting(false);
    }
  }

  function selectCandidate(resultId: number, candidateId: number, personName: string, reason: string) {
    return submit(resultId, { candidate_id: candidateId, person_name: personName, reason });
  }
  function selectManual(resultId: number, fraction: string, nico: string, personName: string, reason: string) {
    return submit(resultId, { fraction, nico, person_name: personName, reason });
  }
  return { selectCandidate, selectManual, deselect, isSubmitting, error, clearError };
}
