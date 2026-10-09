import { useEffect, useState } from "react";
import { listCertificates, useApiClient, type CertificateFilters, type CertificateSummaryDto } from "@/lib/api";

interface SavedState {
  refreshKey: string;
  version: number;
  cursor: string | null;
  items: readonly CertificateSummaryDto[];
  nextCursor: string | null;
  error: unknown;
}

export function useSavedCertificates(refreshKey: string) {
  const api = useApiClient();
  const [version, setVersion] = useState(0);
  const [cursor, setCursor] = useState<string | null>(null);
  const [filters, setFilters] = useState<CertificateFilters>({});
  const [state, setState] = useState<SavedState | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    listCertificates(api, cursor, { signal: controller.signal }, filters).then((result) => {
      if (controller.signal.aborted) return;
      setState({ refreshKey, version, cursor, items: result.data,
        nextCursor: typeof result.meta.next_cursor === "string" ? result.meta.next_cursor : null,
        error: null });
    }).catch((error: unknown) => {
      if (!controller.signal.aborted) setState({ refreshKey, version, cursor, items: [], nextCursor: null, error });
    });
    return () => controller.abort();
  }, [api, cursor, version, refreshKey, filters]);

  return {
    state,
    hasFilters: Object.values(filters).some((value) => Boolean(value?.trim())),
    applyFilters: (next: CertificateFilters) => { setFilters(next); setCursor(null); setVersion((value) => value + 1); },
    loading: state === null || state.version !== version || state.cursor !== cursor || state.refreshKey !== refreshKey,
    reload: () => { setCursor(null); setVersion((value) => value + 1); },
    nextPage: () => setCursor(state?.nextCursor ?? null),
  };
}
