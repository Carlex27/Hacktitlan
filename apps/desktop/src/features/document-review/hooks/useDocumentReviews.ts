import { useCallback, useEffect, useState } from "react";

import {
  isAbortError,
  listDocumentReviews,
  useApiClient,
  type DocumentReviewQueueItemDto,
} from "@/lib/api";

export type DocumentReviewsState =
  | { status: "loading" }
  | { status: "error"; error: unknown }
  | { status: "ready"; items: readonly DocumentReviewQueueItemDto[] };

export interface DocumentReviews {
  state: DocumentReviewsState;
  reload(): void;
}

/** Cola de revisión documental. */
export function useDocumentReviews(): DocumentReviews {
  const api = useApiClient();
  const [version, setVersion] = useState(0);
  // El resultado se guarda con la versión que lo pidió; si no coincide, está cargando.
  const [loaded, setLoaded] = useState<{ version: number; state: DocumentReviewsState } | null>(null);
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

  const state: DocumentReviewsState =
    loaded !== null && loaded.version === version ? loaded.state : { status: "loading" };

  return { state, reload };
}
