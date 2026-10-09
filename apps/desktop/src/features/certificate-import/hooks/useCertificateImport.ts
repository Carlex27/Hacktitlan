import { useCallback, useEffect, useReducer, useRef } from "react";

import {
  describeApiError,
  getJob,
  isAbortError,
  uploadDocument,
  useApiClient,
  type ApiClient,
} from "@/lib/api";

import { createImportItem, isTerminalPhase, type ImportItem } from "../model/importItem";
import { importReducer, type ImportAction } from "../model/importReducer";

export const JOB_POLL_INTERVAL_MS = 1500;

export interface UseCertificateImportOptions {
  pollIntervalMs?: number;
}

export interface CertificateImport {
  items: readonly ImportItem[];
  addFiles(files: readonly File[]): void;
  clearFinished(): void;
  removeCertificate(certificateId: number): void;
}

function delay(ms: number, signal: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(resolve, ms);
    signal.addEventListener(
      "abort",
      () => {
        clearTimeout(timer);
        reject(new DOMException("Aborted", "AbortError"));
      },
      { once: true },
    );
  });
}

async function processFile(
  api: ApiClient,
  item: ImportItem,
  file: File,
  dispatch: (action: ImportAction) => void,
  signal: AbortSignal,
  pollIntervalMs: number,
): Promise<void> {
  try {
    const upload = await uploadDocument(api, file, { signal });
    dispatch({ type: "uploaded", id: item.id, upload });
    if (upload.job_id === null) return;

    for (;;) {
      const job = await getJob(api, upload.job_id, { signal });
      dispatch({ type: "job_updated", id: item.id, job });
      if (isTerminalPhase(job.status)) return;
      await delay(pollIntervalMs, signal);
    }
  } catch (error) {
    if (isAbortError(error)) return;
    dispatch({ type: "failed", id: item.id, message: describeApiError(error) });
  }
}

export function useCertificateImport({
  pollIntervalMs = JOB_POLL_INTERVAL_MS,
}: UseCertificateImportOptions = {}): CertificateImport {
  const api = useApiClient();
  const [items, dispatch] = useReducer(importReducer, []);
  const controllerRef = useRef<AbortController | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    controllerRef.current = controller;
    return () => controller.abort();
  }, []);

  const addFiles = useCallback(
    (files: readonly File[]) => {
      const signal = controllerRef.current?.signal;
      if (!signal || files.length === 0) return;
      const entries = files.map((file) => ({
        file,
        item: createImportItem(crypto.randomUUID(), file.name),
      }));
      dispatch({ type: "added", items: entries.map((entry) => entry.item) });
      for (const { file, item } of entries) {
        void processFile(api, item, file, dispatch, signal, pollIntervalMs);
      }
    },
    [api, pollIntervalMs],
  );

  const clearFinished = useCallback(() => dispatch({ type: "finished_cleared" }), []);
  const removeCertificate = useCallback((certificateId: number) => dispatch({ type: "certificate_deleted", certificateId }), []);

  return { items, addFiles, clearFinished, removeCertificate };
}
