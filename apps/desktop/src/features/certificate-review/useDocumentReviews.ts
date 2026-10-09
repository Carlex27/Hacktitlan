import { useCallback, useEffect, useRef, useState } from "react";
import { getDocumentReviews, reprocessDocument } from "../../lib/api";
import type { DocumentReview } from "../../lib/api";

export function useDocumentReviews(baseUrl: string) {
  const [items, setItems] = useState<DocumentReview[]>([]);
  const [status, setStatus] = useState<"loading" | "empty" | "success" | "needs_review" | "error">("loading");
  const [error, setError] = useState<string | null>(null);
  const [pendingId, setPendingId] = useState<number | null>(null);
  const submitting = useRef(false);
  const reload = useCallback(async () => {
    setStatus("loading");
    setError(null);
    try {
      const data = await getDocumentReviews(baseUrl);
      setItems(data);
      setStatus(data.length ? "needs_review" : "empty");
      return true;
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : String(failure));
      setStatus("error");
      return false;
    }
  }, [baseUrl]);
  useEffect(() => { void reload(); }, [reload]);
  const reprocess = async (id: number, person: string, reason: string) => {
    if (submitting.current) return;
    submitting.current = true;
    setPendingId(id);
    setError(null);
    try {
      await reprocessDocument(baseUrl, id, person, reason);
      if (await reload()) setStatus("success");
    } catch (failure) {
      await reload();
      setError(failure instanceof Error ? failure.message : String(failure));
    } finally {
      submitting.current = false;
      setPendingId(null);
    }
  };
  return { items, status, error, pendingId, reload, reprocess };
}
