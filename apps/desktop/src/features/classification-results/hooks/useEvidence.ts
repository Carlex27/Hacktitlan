import { useCallback, useEffect, useRef, useState } from "react";

import { getEvidence, isAbortError, useApiClient, type EvidenceDetailDto } from "@/lib/api";

export type EvidenceState =
  | { status: "idle" }
  | { status: "loading"; linkId: number }
  | { status: "success"; linkId: number; evidence: EvidenceDetailDto }
  | { status: "error"; linkId: number; error: unknown };

export interface UseEvidenceResult {
  state: EvidenceState;
  /** Abre una evidencia; cancela la solicitud anterior si seguía en curso. */
  open(linkId: number): void;
  retry(): void;
  close(): void;
}

/**
 * Carga evidencia bajo demanda. No lanza errores: los expone en `state` para
 * que la interfaz los muestre en lugar de producir promesas sin manejar.
 */
export function useEvidence(): UseEvidenceResult {
  const api = useApiClient();
  const [state, setState] = useState<EvidenceState>({ status: "idle" });
  const controllerRef = useRef<AbortController | null>(null);

  useEffect(() => () => controllerRef.current?.abort(), []);

  const open = useCallback(
    (linkId: number) => {
      controllerRef.current?.abort();
      const controller = new AbortController();
      controllerRef.current = controller;
      setState({ status: "loading", linkId });

      getEvidence(api, linkId, { signal: controller.signal })
        .then((evidence) => {
          if (!controller.signal.aborted) setState({ status: "success", linkId, evidence });
        })
        .catch((error: unknown) => {
          if (controller.signal.aborted || isAbortError(error)) return;
          setState({ status: "error", linkId, error });
        });
    },
    [api],
  );

  const retry = useCallback(() => {
    if (state.status !== "idle") open(state.linkId);
  }, [open, state]);

  const close = useCallback(() => {
    controllerRef.current?.abort();
    controllerRef.current = null;
    setState({ status: "idle" });
  }, []);

  return { state, open, retry, close };
}
