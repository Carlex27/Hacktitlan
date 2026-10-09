import { useState } from "react";
import { acceptFieldVerification, useApiClient } from "@/lib/api";

export function useVerificationCorrection(observationId: number) {
  const api = useApiClient();
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [saved, setSaved] = useState(false);
  async function accept(person_name: string, reason: string) {
    if (isSaving) return false;
    setIsSaving(true);
    setError(null);
    try {
      await acceptFieldVerification(api, observationId, { person_name, reason });
      setSaved(true);
      return true;
    } catch (failure: unknown) {
      setError(failure);
      return false;
    } finally {
      setIsSaving(false);
    }
  }
  return { accept, isSaving, error, saved };
}
