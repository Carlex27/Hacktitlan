import { useCallback, useEffect, useState } from "react";

import {
  getClassificationRun,
  listClassificationRuns,
  useApiClient,
  type ApiError,
  type ClassificationRunDto,
  type ClassificationRunSummaryDto,
} from "@/lib/api";

export interface UseClassificationRunResult {
  run: ClassificationRunDto | null;
  runsList: readonly ClassificationRunSummaryDto[];
  isLoading: boolean;
  error: ApiError | null;
  reload: () => void;
}

interface RunState {
  certificateId: number | null;
  version: number;
  runsList: readonly ClassificationRunSummaryDto[];
  run: ClassificationRunDto | null;
  error: ApiError | null;
}

export function useClassificationRun(
  certificateId: number | null,
): UseClassificationRunResult {
  const api = useApiClient();
  const [version, setVersion] = useState(0);
  const [state, setState] = useState<RunState>({
    certificateId: null,
    version: 0,
    runsList: [],
    run: null,
    error: null,
  });

  const reload = useCallback(() => {
    setVersion((v) => v + 1);
  }, []);

  useEffect(() => {
    if (certificateId === null) return;

    const controller = new AbortController();
    let isCurrent = true;

    listClassificationRuns(api, certificateId, { signal: controller.signal })
      .then(async (summaries) => {
        if (!isCurrent) return;
        const latest = summaries[0];
        if (!latest) {
          setState({
            certificateId,
            version,
            runsList: summaries,
            run: null,
            error: null,
          });
          return;
        }

        const detail = await getClassificationRun(api, latest.id, {
          signal: controller.signal,
        });
        if (!isCurrent) return;
        setState({
          certificateId,
          version,
          runsList: summaries,
          run: detail,
          error: null,
        });
      })
      .catch((err: unknown) => {
        if (!isCurrent || controller.signal.aborted) return;
        setState({
          certificateId,
          version,
          runsList: [],
          run: null,
          error: err as ApiError,
        });
      });

    return () => {
      isCurrent = false;
      controller.abort();
    };
  }, [api, certificateId, version]);

  const isMatched =
    certificateId !== null &&
    state.certificateId === certificateId &&
    state.version === version;

  const runsList = isMatched ? state.runsList : [];
  const run = isMatched ? state.run : null;
  const error = isMatched ? state.error : null;
  const isLoading = certificateId !== null && !isMatched;

  return { run, runsList, isLoading, error, reload };
}
