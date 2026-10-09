import { useState } from "react";
import { reprocessCertificate, useApiClient } from "@/lib/api";
import { es } from "@/lib/i18n";

export function useDocumentReprocess(certificateId: number, onQueued: () => void) {
  const api = useApiClient();
  const [submitting, setSubmitting] = useState(false);
  const [queued, setQueued] = useState(false);
  const [error, setError] = useState<unknown>(null);

  async function start() {
    setSubmitting(true);
    setError(null);
    try {
      await reprocessCertificate(api, certificateId, {
        from_stage: "extraction",
        person_name: "Administrador",
        reason: es.documentReview.reanalyzeReason,
      });
      setQueued(true);
      onQueued();
    } catch (cause) { setError(cause); }
    finally { setSubmitting(false); }
  }

  return { submitting, queued, error, start };
}
