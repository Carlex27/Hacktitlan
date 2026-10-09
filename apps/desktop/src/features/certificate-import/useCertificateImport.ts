import { useEffect, useRef, useState } from "react";

import { getDocumentJob, uploadDocumentLegacy as uploadDocument } from "../../lib/api";
import type { DocumentJob, DocumentUpload } from "../../lib/api";

type ImportStatus = "loading" | "empty" | "success" | "needs_review" | "error";
export interface ImportedFile {
  name: string;
  receipt: DocumentUpload;
  job: DocumentJob | null;
  trackingError: string | null;
}

function isPending(item: ImportedFile) {
  return item.receipt.job_id !== null && !item.trackingError &&
    (!item.job || item.job.status === "queued" || item.job.status === "running");
}

export function useCertificateImport(apiBaseUrl: string) {
  const [files, setFiles] = useState<readonly File[]>([]);
  const [receipts, setReceipts] = useState<ImportedFile[]>([]);
  const [uploadStatus, setStatus] = useState<ImportStatus>("empty");
  const [error, setError] = useState<string | null>(null);
  const submitting = useRef(false);
  const pending = receipts.filter(isPending);
  const status: ImportStatus = uploadStatus === "loading" || pending.length ? "loading"
    : error || receipts.some((item) => item.trackingError || item.job?.status === "failed" || item.job?.status === "cancelled") ? "error"
    : receipts.some((item) => item.job?.status === "needs_review" || item.job?.status === "needs_ocr") ? "needs_review"
    : uploadStatus;

  useEffect(() => {
    const active = receipts.filter(isPending);
    if (!active.length) return;
    const controller = new AbortController();
    const timer = setTimeout(async () => {
      const updates = await Promise.all(active.map(async (item) => {
        const jobId = item.receipt.job_id;
        if (jobId === null) return item;
        try {
          const job = await getDocumentJob(apiBaseUrl, jobId, controller.signal);
          return { ...item, job };
        } catch (failure) {
          return { ...item, trackingError: failure instanceof Error ? failure.message : String(failure) };
        }
      }));
      if (!controller.signal.aborted) setReceipts((current) => current.map((item) =>
        {
          const update = updates.find((entry) => entry.receipt.document_id === item.receipt.document_id);
          return update ? { ...item, job: update.job, trackingError: update.trackingError } : item;
        }));
    }, 1000);
    return () => { clearTimeout(timer); controller.abort(); };
  }, [apiBaseUrl, receipts]);

  const retryTracking = (documentId: number) => setReceipts((current) => current.map((item) =>
    item.receipt.document_id === documentId ? { ...item, trackingError: null } : item));

  const selectFiles = (selected: readonly File[]) => {
    if (submitting.current || status === "loading") return;
    setFiles(selected);
    setReceipts([]);
    setError(null);
    setStatus("empty");
  };
  const submit = async () => {
    if (submitting.current || status === "loading" || files.length === 0) return;
    submitting.current = true;
    setStatus("loading");
    setError(null);
    setReceipts([]);
    try {
      for (const file of files) {
        const receipt = await uploadDocument(apiBaseUrl, file);
        setReceipts((current) => [...current, { name: file.name, receipt, job: null, trackingError: null }]);
      }
      setStatus("success");
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : String(failure));
      setStatus("error");
    } finally {
      submitting.current = false;
    }
  };
  return { files, receipts, status, error, uploading: uploadStatus === "loading", selectFiles, submit, retryTracking };
}
