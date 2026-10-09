import { useCallback, useEffect, useState } from "react";

import { isAbortError, useApiClient } from "@/lib/api";

export type PdfObjectUrlState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "ready"; objectUrl: string; isPdf: boolean }
  | { status: "error"; error: unknown };

interface Loaded {
  key: string;
  state: PdfObjectUrlState;
}

/**
 * Descarga el PDF por el cliente del API y lo expone como URL local (`blob:`).
 * Así el visor lo muestra aunque el servidor lo envíe como descarga, y los
 * errores del servidor se presentan en lugar de verse dentro del iframe.
 */
export function usePdfObjectUrl(filePath: string | null): { state: PdfObjectUrlState; reload(): void } {
  const api = useApiClient();
  const [version, setVersion] = useState(0);
  const [loaded, setLoaded] = useState<Loaded | null>(null);
  const key = filePath === null ? null : `${filePath}|${version}`;

  useEffect(() => {
    if (filePath === null || key === null) return;
    const controller = new AbortController();
    let objectUrl: string | null = null;

    api
      .getBlob(filePath, { signal: controller.signal })
      .then((blob) => {
        if (controller.signal.aborted) return;
        objectUrl = URL.createObjectURL(blob);
        setLoaded({ key, state: { status: "ready", objectUrl, isPdf: blob.type.split(";")[0] === "application/pdf" } });
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted || isAbortError(error)) return;
        setLoaded({ key, state: { status: "error", error } });
      });

    return () => {
      controller.abort();
      if (objectUrl !== null) URL.revokeObjectURL(objectUrl);
    };
  }, [api, filePath, key]);

  const reload = useCallback(() => setVersion((value) => value + 1), []);

  if (filePath === null) return { state: { status: "idle" }, reload };
  if (loaded === null || loaded.key !== key) return { state: { status: "loading" }, reload };
  return { state: loaded.state, reload };
}
