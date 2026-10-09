import { useEffect, useRef, useState } from "react";
import { ApiError, createExport, getExport, useApiClient } from "@/lib/api";
import { es } from "@/lib/i18n";

export function useCertificateExport(certificateId: number) {
  const api = useApiClient();
  const [exportId, setExportId] = useState<number | null>(null);
  const [state, setState] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [error, setError] = useState<unknown>(null);
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null);
  const submitting = useRef(false);
  const request = useRef<AbortController | null>(null);
  useEffect(() => () => request.current?.abort(), []);
  useEffect(() => {
    if (exportId === null) return;
    const activeExportId = exportId;
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout> | undefined;
    async function poll() {
      try {
        const result = await getExport(api, activeExportId, { signal: controller.signal });
        if (controller.signal.aborted) return;
        if (result.status === "failed") throw new ApiError({ kind: "server", message: result.error_message ?? es.certificateExport.failed });
        if (result.status === "succeeded") {
          if (!result.download_url) throw new ApiError({ kind: "invalid_response", message: es.certificateExport.failed });
          setDownloadUrl(api.url(result.download_url));
          setState("success");
        } else timer = setTimeout(poll, 1500);
      } catch (cause) {
        if (!controller.signal.aborted) { setError(cause); setState("error"); }
      }
    }
    void poll();
    return () => { controller.abort(); clearTimeout(timer); };
  }, [api, exportId]);
  async function generate() {
    if (submitting.current) return;
    submitting.current = true;
    const controller = new AbortController();
    request.current = controller;
    setState("loading"); setError(null); setDownloadUrl(null); setExportId(null);
    try {
      const result = await createExport(api, { certificate_ids: [certificateId], official: false,
        person_name: "Administrador" }, { signal: controller.signal });
      if (!controller.signal.aborted) setExportId(result.export_id);
    } catch (cause) {
      if (!controller.signal.aborted) { setError(cause); setState("error"); }
    } finally { submitting.current = false; }
  }
  return { state, error, downloadUrl, generate };
}
