import { FileTextIcon } from "lucide-react";

import { ProcessingStatusBadge } from "@/components/feedback";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { es } from "@/lib/i18n";

import { describeItem } from "../model/describeItem";
import { phaseToStatus, type ImportItem } from "../model/importItem";

export interface ImportQueueItemProps {
  item: ImportItem;
  onReview?: ((certificateId: number, documentId?: number | null) => void) | undefined;
}

export function ImportQueueItem({ item, onReview }: ImportQueueItemProps) {
  const status = phaseToStatus(item.phase);
  const showProgress = status === "loading" && item.progress !== null;

  return (
    <li className="flex flex-wrap items-start gap-3 py-4" data-status={status}>
      <FileTextIcon aria-hidden="true" className="mt-0.5 size-5 shrink-0 text-muted-foreground" />
      <div className="flex min-w-0 flex-1 flex-col gap-1">
        <div className="flex items-center gap-2">
          <span className="truncate font-medium" title={item.fileName}>
            {item.fileName}
          </span>
          {item.duplicate && (
            <Badge variant="outline">{es.certificateImport.item.duplicate}</Badge>
          )}
        </div>
        <p
          className={status === "error" ? "text-sm text-destructive" : "text-sm text-muted-foreground"}
        >
          {describeItem(item)}
          {item.certificateId !== null && (
            <> · {es.certificateImport.item.certificateRef(item.certificateId)}</>
          )}
        </p>
        {item.errorMessage && item.phase !== "request_failed" && (
          <p className="text-sm text-destructive">{item.errorMessage}</p>
        )}
        {showProgress && (
          <Progress
            value={item.progress}
            aria-label={es.certificateImport.item.progressLabel(item.fileName)}
          />
        )}
      </div>

      <div className="flex items-center gap-2 shrink-0">
        {item.certificateId !== null && onReview && (
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => {
              const certId = item.certificateId;
              if (certId !== null) {
                onReview(certId, item.documentId);
              }
            }}
            className="min-h-9"
          >
            {es.certificateImport.item.reviewAction}
          </Button>
        )}
        <ProcessingStatusBadge status={status} />
      </div>
    </li>
  );
}
