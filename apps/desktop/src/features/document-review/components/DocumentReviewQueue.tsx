import { ClipboardCheckIcon, RefreshCwIcon } from "lucide-react";

import { LoadErrorAlert } from "@/components/feedback";
import { Button } from "@/components/ui/button";
import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Empty, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from "@/components/ui/empty";
import { Skeleton } from "@/components/ui/skeleton";
import { es } from "@/lib/i18n";

import { useDocumentReviews } from "../hooks/useDocumentReviews";
import { DocumentReviewItem } from "./DocumentReviewItem";

export interface DocumentReviewQueueProps {
  onReview?: (certificateId: number, documentId: number) => void;
}

/** Cola de actas con incidencias de calidad. */
export function DocumentReviewQueue({ onReview }: DocumentReviewQueueProps) {
  const reviews = useDocumentReviews();
  const { state } = reviews;

  return (
    <Card className="rounded-xl border-border shadow-none">
      <CardHeader>
        <CardTitle>
          <h3 className="text-lg leading-7 font-semibold">{es.documentReview.title}</h3>
        </CardTitle>
        <CardDescription>{es.documentReview.description}</CardDescription>
        <CardAction>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={reviews.reload}
            disabled={state.status === "loading"}
          >
            <RefreshCwIcon data-icon="inline-start" aria-hidden="true" />
            {es.documentReview.refresh}
          </Button>
        </CardAction>
      </CardHeader>
      <CardContent className="flex flex-col gap-2">
        {state.status === "loading" && (
          <div role="status" aria-label={es.documentReview.loading} className="flex flex-col gap-2">
            <Skeleton className="h-14 w-full" />
            <Skeleton className="h-14 w-full" />
          </div>
        )}

        {state.status === "error" && (
          <LoadErrorAlert title={es.documentReview.loadError} error={state.error} onRetry={reviews.reload} />
        )}

        {state.status === "ready" && state.items.length === 0 && (
          <Empty>
            <EmptyHeader>
              <EmptyMedia variant="icon">
                <ClipboardCheckIcon aria-hidden="true" />
              </EmptyMedia>
              <EmptyTitle>{es.documentReview.emptyTitle}</EmptyTitle>
              <EmptyDescription>{es.documentReview.emptyDescription}</EmptyDescription>
            </EmptyHeader>
          </Empty>
        )}

        {state.status === "ready" && state.items.length > 0 && (
          <ul aria-label={es.documentReview.title} className="flex flex-col divide-y">
            {state.items.map((item) => (
              <DocumentReviewItem
                key={item.certificate_id}
                item={item}
                onReprocessed={reviews.reload}
                {...(onReview ? { onReview } : {})}
              />
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
