import { useCallback, useEffect, useState } from "react";

import { isAbortError, useApiClient } from "@/lib/api";

import { checkConnection, type ConnectionState } from "../model/checkConnection";

export interface BackendConnection {
  state: ConnectionState;
  /** `true` mientras se repite la comprobación tras un fallo. */
  isRetrying: boolean;
  retry(): void;
}

export function useBackendConnection(): BackendConnection {
  const api = useApiClient();
  const [state, setState] = useState<ConnectionState>({ status: "checking" });
  const [attempt, setAttempt] = useState(0);
  const [isRetrying, setIsRetrying] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    checkConnection(api, controller.signal)
      .then((next) => {
        setState(next);
        setIsRetrying(false);
      })
      .catch((error: unknown) => {
        if (isAbortError(error)) return;
        throw error;
      });
    return () => controller.abort();
  }, [api, attempt]);

  const retry = useCallback(() => {
    setIsRetrying(true);
    setAttempt((value) => value + 1);
  }, []);

  return { state, isRetrying, retry };
}
