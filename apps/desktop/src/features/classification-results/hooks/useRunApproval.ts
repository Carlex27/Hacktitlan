import { useState } from "react";

import {
  approveClassificationRun,
  rejectClassificationRun,
  saveClassificationDraft,
  useApiClient,
  type ApiError,
  type RunApprovalResultDto,
} from "@/lib/api";

export interface UseRunApprovalResult {
  approveRun(runId: number, personName: string, reason: string): Promise<RunApprovalResultDto>;
  rejectRun(runId: number, personName: string, reason: string): Promise<RunApprovalResultDto>;
  saveDraft(runId: number, personName: string, reason: string): Promise<RunApprovalResultDto>;
  isSubmitting: boolean;
  error: ApiError | null;
  clearError(): void;
}

export function useRunApproval(): UseRunApprovalResult {
  const api = useApiClient();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);

  async function approveRun(
    runId: number,
    personName: string,
    reason: string,
  ): Promise<RunApprovalResultDto> {
    setIsSubmitting(true);
    setError(null);
    try {
      const res = await approveClassificationRun(api, runId, {
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

  async function rejectRun(
    runId: number,
    personName: string,
    reason: string,
  ): Promise<RunApprovalResultDto> {
    setIsSubmitting(true);
    setError(null);
    try {
      const res = await rejectClassificationRun(api, runId, {
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

  async function saveDraft(runId: number, personName: string, reason: string) {
    setIsSubmitting(true);
    setError(null);
    try {
      return await saveClassificationDraft(api, runId, { person_name: personName, reason });
    } catch (err) {
      setError(err as ApiError);
      throw err;
    } finally {
      setIsSubmitting(false);
    }
  }

  function clearError() {
    setError(null);
  }

  return { approveRun, rejectRun, saveDraft, isSubmitting, error, clearError };
}
