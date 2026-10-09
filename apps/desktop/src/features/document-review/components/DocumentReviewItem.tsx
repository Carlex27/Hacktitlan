import { ProcessingStatusBadge } from "@/components/feedback";
import { Badge } from "@/components/ui/badge";
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

      {item.active_job_id !== null && (
        <p role="status" className="text-[11px] text-slate-600">{es.documentReview.activeJob(item.active_job_id)}</p>
      )}

    </li>
  );
}
