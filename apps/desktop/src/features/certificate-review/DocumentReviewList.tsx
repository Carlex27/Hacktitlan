import { useState } from "react";
import type { FormEvent } from "react";
import type { DocumentReview } from "../../lib/api";
import { reviewTexts as texts } from "./texts";
import { useDocumentReviews } from "./useDocumentReviews";

function ReviewItem({ item, busy, onReprocess }: {
  item: DocumentReview;
  busy: boolean;
  onReprocess: (id: number, person: string, reason: string) => Promise<void>;
}) {
  const [person, setPerson] = useState("");
  const [reason, setReason] = useState("");
  const disabled = busy || !item.can_reprocess;
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!disabled && person.trim() && reason.trim()) {
      void onReprocess(item.certificate_id, person.trim(), reason.trim());
    }
  }
  return <li>
    <p>{item.certificate_no ?? `#${item.certificate_id}`} · Revisión {item.revision_number} · {item.document_status}</p>
    {item.active_job_id !== null && <p aria-live="polite">Trabajo activo: {item.active_job_id}</p>}
    <form onSubmit={submit}>
      <fieldset disabled={disabled}>
        <legend>{texts.reprocess}</legend>
        <label>{texts.person}<input required value={person} onChange={event => setPerson(event.target.value)} /></label>
        <label>{texts.reason}<input required value={reason} onChange={event => setReason(event.target.value)} /></label>
        <button type="submit" disabled={disabled || !person.trim() || !reason.trim()}>{disabled ? texts.processing : texts.reprocess}</button>
      </fieldset>
    </form>
  </li>;
}

export function DocumentReviewList({ apiBaseUrl }: { apiBaseUrl: string }) {
  const reviews = useDocumentReviews(apiBaseUrl);
  return <section aria-labelledby="document-review-title">
    <h2 id="document-review-title">{texts.title}</h2>
    <button onClick={() => void reviews.reload()} disabled={reviews.status === "loading"}>{texts.refresh}</button>
    {reviews.status === "loading" && <p role="status">{texts.loading}</p>}
    {reviews.status === "empty" && <p>{texts.empty}</p>}
    {reviews.status === "success" && <p role="status">{texts.success}</p>}
    {reviews.error && <p role="alert">{reviews.error}</p>}
    <ul>{reviews.items.map(item => <ReviewItem key={item.certificate_id} item={item} busy={reviews.pendingId !== null} onReprocess={reviews.reprocess} />)}</ul>
  </section>;
}
