import { useCallback, useEffect, useRef, useState } from "react";

import {
  getLigieEntries,
  isAbortError,
  useApiClient,
  type LigieEntriesMetaDto,
  type LigieEntryDto,
} from "@/lib/api";

interface Target {
  /** Código enviado al backend (sólo dígitos). */
  code: string;
  /** Código como se muestra en la interfaz. */
  label: string;
}

export type TariffReferenceState =
  | { status: "idle" }
  | ({ status: "loading" } & Target)
  | ({ status: "error"; error: unknown } & Target)
  | ({
      status: "success";
      entries: readonly LigieEntryDto[];
      meta: LigieEntriesMetaDto;
      /** Aparición elegida cuando la fuente repite el código. */
      activeIndex: number;
    } & Target);

export interface TariffReference {
  state: TariffReferenceState;
  open(code: string, label: string): void;
  selectEntry(index: number): void;
  retry(): void;
}

/** Consulta bajo demanda la página de una fracción o NICO en la LIGIE fuente. */
export function useTariffReference(): TariffReference {
  const api = useApiClient();
  const [state, setState] = useState<TariffReferenceState>({ status: "idle" });
  const controllerRef = useRef<AbortController | null>(null);

  useEffect(() => () => controllerRef.current?.abort(), []);

  const open = useCallback(
    (code: string, label: string) => {
      controllerRef.current?.abort();
      const controller = new AbortController();
      controllerRef.current = controller;
      setState({ status: "loading", code, label });

      getLigieEntries(api, code, { signal: controller.signal })
        .then(({ entries, meta }) => {
          if (controller.signal.aborted) return;
          setState({ status: "success", code, label, entries, meta, activeIndex: 0 });
        })
        .catch((error: unknown) => {
          if (controller.signal.aborted || isAbortError(error)) return;
          setState({ status: "error", code, label, error });
        });
    },
    [api],
  );

  const selectEntry = useCallback((index: number) => {
    setState((current) =>
      current.status === "success" && index >= 0 && index < current.entries.length
        ? { ...current, activeIndex: index }
        : current,
    );
  }, []);

  const retry = useCallback(() => {
    if (state.status !== "idle") open(state.code, state.label);
  }, [open, state]);

  return { state, open, selectEntry, retry };
}
