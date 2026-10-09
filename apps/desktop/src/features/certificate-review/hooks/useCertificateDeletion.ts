import { useRef, useState } from "react";
import { deleteCertificate, useApiClient } from "@/lib/api";

export function useCertificateDeletion(certificateId: number) {
  const api = useApiClient();
  const pending = useRef(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [error, setError] = useState<unknown>(null);

  async function remove() {
    if (pending.current) return false;
    pending.current = true;
    setIsDeleting(true);
    setError(null);
    try {
      await deleteCertificate(api, certificateId);
      return true;
    } catch (failure: unknown) {
      setError(failure);
      return false;
    } finally {
      pending.current = false;
      setIsDeleting(false);
    }
  }
  return { remove, isDeleting, error };
}
