import { ArrowRightIcon } from "lucide-react";

import { ProcessingStatusBadge } from "@/components/feedback";
import { Button } from "@/components/ui/button";
import type { DocumentReviewQueueItemDto } from "@/lib/api";
import { es } from "@/lib/i18n";

import { reviewItemStatus } from "../model/reviewItem";

export interface DocumentReviewItemProps {
  item: DocumentReviewQueueItemDto;
  onReview?: (certificateId: number, documentId: number) => void;
}

export function DocumentReviewItem({
  item,
  onReview,
}: DocumentReviewItemProps) {
  const label = item.source_file_name?.toLowerCase().endsWith(".xlsx")
    ? item.source_file_name
    : es.documentReview.certificateLabel(item.certificate_no, item.certificate_id);
  const headingId = `review-item-${item.certificate_id}`;
  const status = reviewItemStatus(item);

  return (
    <li aria-labelledby={headingId} data-status={reviewItemStatus(item)} className="grid min-w-0 gap-4 py-5 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center">
      <div className="min-w-0 space-y-1">
        <h4 id={headingId} className="text-base leading-6 font-semibold text-foreground">{label}</h4>
        {item.manufacturer && (
          <p className="text-sm leading-5 text-muted-foreground">{item.manufacturer}</p>
        )}
        <p className="text-xs leading-5 text-muted-foreground">{es.documentReview.revision(item.revision_number)}</p>
        {item.active_job_id !== null && (
          <p role="status" className="text-sm leading-5 text-muted-foreground">{es.documentReview.activeJob(item.active_job_id)}</p>
        )}
      </div>
      <div className="flex flex-wrap items-center justify-between gap-4 sm:justify-end">
        <ProcessingStatusBadge status={status} className={`h-7 px-3 ${status === "needs_review" ? "border-warning-border bg-warning-background text-warning-foreground" : status === "success" ? "bg-secondary text-secondary-foreground" : ""}`} />
        {onReview && (
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="min-h-11 shrink-0"
            onClick={() => onReview(item.certificate_id, item.document_id)}
          >
            {es.documentReview.review}
            <ArrowRightIcon aria-hidden="true" data-icon="inline-end" />
          </Button>
        )}
      </div>

    </li>
  );
}
