import { InboxIcon } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardAction, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty";
import { es } from "@/lib/i18n";

import { isTerminalPhase, visibleImportItems, type ImportItem } from "../model/importItem";
import { ImportQueueItem } from "./ImportQueueItem";

export interface ImportQueueProps {
  items: readonly ImportItem[];
  onClearFinished(): void;
  onReview?: ((certificateId: number, documentId?: number | null) => void) | undefined;
}

export function ImportQueue({ items, onClearFinished, onReview }: ImportQueueProps) {
  const visibleItems = visibleImportItems(items);
  const hasFinished = visibleItems.some((item) => isTerminalPhase(item.phase));

  return (
    <Card className="rounded-xl border-border shadow-none">
      <CardHeader>
        <CardTitle>
          <h3 className="text-lg leading-7 font-semibold">{es.certificateImport.queue.title}</h3>
        </CardTitle>
        {hasFinished && (
          <CardAction>
            <Button variant="ghost" size="sm" onClick={onClearFinished}>
              {es.certificateImport.queue.clearFinished}
            </Button>
          </CardAction>
        )}
      </CardHeader>
      <CardContent>
        {visibleItems.length === 0 ? (
          <Empty>
            <EmptyHeader>
              <EmptyMedia variant="icon">
                <InboxIcon aria-hidden="true" />
              </EmptyMedia>
              <EmptyTitle>{es.certificateImport.queue.emptyTitle}</EmptyTitle>
              <EmptyDescription>{es.certificateImport.queue.emptyDescription}</EmptyDescription>
            </EmptyHeader>
          </Empty>
        ) : (
          <ul aria-live="polite" className="flex flex-col divide-y">
            {visibleItems.map((item) => (
              <ImportQueueItem key={item.id} item={item} onReview={onReview} />
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
