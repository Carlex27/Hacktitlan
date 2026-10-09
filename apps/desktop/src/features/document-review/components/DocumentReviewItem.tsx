import { LoadErrorAlert, ProcessingStatusBadge } from "@/components/feedback";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { DocumentReviewQueueItemDto } from "@/lib/api";
import { es } from "@/lib/i18n";

import { reviewItemStatus } from "../model/reviewItem";
import { ReprocessForm } from "./ReprocessForm";

export interface DocumentReviewItemProps {
  item: DocumentReviewQueueItemDto;
  /** Hay una solicitud de reprocesamiento en curso (de esta u otra acta). */
  busy: boolean;
  isSubmitting: boolean;
  reprocessError: unknown;
  onReprocess(personName: string, reason: string): Promise<boolean>;
  onReview?: (certificateId: number, documentId: number) => void;
}

export function DocumentReviewItem({
  item,
  busy,
  isSubmitting,
  reprocessError,
  onReprocess,
  onReview,
}: DocumentReviewItemProps) {
  const label = es.documentReview.certificateLabel(item.certificate_no, item.certificate_id);
  const headingId = `review-item-${item.certificate_id}`;

  return (
    <li aria-labelledby={headingId} data-status={reviewItemStatus(item)} className="flex flex-col gap-2 py-3">
      <div className="flex flex-wrap items-center gap-2">
        <span id={headingId} className="font-semibold text-slate-800">{label}</span>
        <Badge variant="outline">{es.documentReview.revision(item.revision_number)}</Badge>
        <ProcessingStatusBadge status={reviewItemStatus(item)} />
        {onReview && (
          <Button
            type="button"
            variant="ghost"
            size="sm"
            className="ml-auto"
            onClick={() => onReview(item.certificate_id, item.document_id)}
          >
            {es.documentReview.review}
          </Button>
        )}
      </div>

      <p className="flex flex-wrap gap-x-3 text-[11px] text-slate-500">
        {item.manufacturer && <span>{item.manufacturer}</span>}
        <span>{es.documentReview.qualityScore(item.quality_score)}</span>
        <span>{es.documentReview.blocking(item.blocking_issues_count)}</span>
        <span>{es.documentReview.warnings(item.warning_issues_count)}</span>
      </p>

      {item.issues_summary.length > 0 && (
        <ul className="flex flex-col gap-0.5 text-[11px] text-slate-600">
          {item.issues_summary.map((issue, index) => (
            <li key={`${issue.code}-${issue.field_path}-${index}`}>
              <span className={issue.severity === "blocking" ? "font-semibold text-destructive" : "font-semibold text-amber-700"}>
                {issue.field_path}
              </span>
              {" — "}
              {issue.message}
            </li>
          ))}
        </ul>
      )}

      {item.active_job_id !== null && (
        <p role="status" className="text-[11px] text-slate-600">{es.documentReview.activeJob(item.active_job_id)}</p>
      )}

      {reprocessError !== null && reprocessError !== undefined && (
        <LoadErrorAlert title={es.documentReview.reprocessError} error={reprocessError} />
      )}

      <ReprocessForm
        disabled={!item.can_reprocess || busy}
        isSubmitting={isSubmitting}
        onSubmit={onReprocess}
      />
    </li>
  );
}
