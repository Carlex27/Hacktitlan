import { useState } from "react";

import {
  selectClassificationCandidate,
  useApiClient,
  type ApiError,
  type CandidateSelectionDto,
} from "@/lib/api";

export interface UseCandidateSelectionResult {
  selectCandidate(
    resultId: number,
    candidateId: number,
    personName: string,
    reason: string,
  ): Promise<CandidateSelectionDto>;
  isSubmitting: boolean;
  error: ApiError | null;
  clearError(): void;
}

export function useCandidateSelection(): UseCandidateSelectionResult {
  const api = useApiClient();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);

  async function selectCandidate(
    resultId: number,
    candidateId: number,
    personName: string,
    reason: string,
  ): Promise<CandidateSelectionDto> {
    setIsSubmitting(true);
    setError(null);
    try {
      const res = await selectClassificationCandidate(api, resultId, {
        candidate_id: candidateId,
        person_name: personName,
        reason,
      });
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

  return { selectCandidate, isSubmitting, error, clearError };
}
