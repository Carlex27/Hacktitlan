import { useCallback, useEffect, useState } from "react";

import {
  isAbortError,
  listDocumentReviews,
  reprocessCertificate,
  useApiClient,
  type DocumentReviewQueueItemDto,
  type ReprocessResultDto,
} from "@/lib/api";

export type DocumentReviewsState =
  | { status: "loading" }
  | { status: "error"; error: unknown }
  | { status: "ready"; items: readonly DocumentReviewQueueItemDto[] };

export interface ReprocessState {
  pendingCertificateId: number | null;
  /** Último error de reprocesamiento y el acta a la que corresponde. */
  error: { certificateId: number; error: unknown } | null;
  lastResult: ReprocessResultDto | null;
}

export interface DocumentReviews {
  state: DocumentReviewsState;
  reprocess: ReprocessState;
  reload(): void;
  reprocessCertificate(certificateId: number, personName: string, reason: string): Promise<boolean>;
}

/** Cola de revisión documental y reprocesamiento desde extracción. */
export function useDocumentReviews(): DocumentReviews {
  const api = useApiClient();
  const [version, setVersion] = useState(0);
  // El resultado se guarda con la versión que lo pidió; si no coincide, está cargando.
  const [loaded, setLoaded] = useState<{ version: number; state: DocumentReviewsState } | null>(null);
  const [reprocess, setReprocess] = useState<ReprocessState>({
    pendingCertificateId: null,
    error: null,
    lastResult: null,
  });

  useEffect(() => {
    const controller = new AbortController();
    listDocumentReviews(api, {}, { signal: controller.signal })
      .then((items) => {
        if (!controller.signal.aborted) setLoaded({ version, state: { status: "ready", items } });
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted || isAbortError(error)) return;
        setLoaded({ version, state: { status: "error", error } });
      });
    return () => controller.abort();
  }, [api, version]);

  const reload = useCallback(() => setVersion((value) => value + 1), []);

  const runReprocess = useCallback(
    async (certificateId: number, personName: string, reason: string) => {
      // Una solicitud a la vez: evita encolar dos extracciones del mismo PDF.
      if (reprocess.pendingCertificateId !== null) return false;
      setReprocess({ pendingCertificateId: certificateId, error: null, lastResult: null });
      try {
        const result = await reprocessCertificate(api, certificateId, {
          from_stage: "extraction",
          person_name: personName,
          reason,
        });
        setReprocess({ pendingCertificateId: null, error: null, lastResult: result });
        return true;
      } catch (error) {
        setReprocess({ pendingCertificateId: null, error: { certificateId, error }, lastResult: null });
        return false;
      } finally {
        // Con éxito o con 409 (`reprocess_in_progress`) la cola cambió: se vuelve a consultar.
        reload();
      }
    },
    [api, reload, reprocess.pendingCertificateId],
  );

  const state: DocumentReviewsState =
    loaded !== null && loaded.version === version ? loaded.state : { status: "loading" };

  return { state, reprocess, reload, reprocessCertificate: runReprocess };
}
