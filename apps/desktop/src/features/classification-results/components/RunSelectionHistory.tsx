import { LoadErrorAlert } from "@/components/feedback";
import { Skeleton } from "@/components/ui/skeleton";
import type { ClassificationRunDto } from "@/lib/api";
import { es } from "@/lib/i18n";

import { SelectionHistory } from "./SelectionHistory";

export interface RunSelectionHistoryProps {
  run: ClassificationRunDto | null;
  isLoading?: boolean;
  error?: unknown;
  onRetry?: () => void;
}

/** Historial de selecciones de todos los productos de la ejecución. */
export function RunSelectionHistory({
  run,
  isLoading = false,
  error = null,
  onRetry,
}: RunSelectionHistoryProps) {
  if (error) {
    return (
      <LoadErrorAlert
        title={es.classification.loadError}
        error={error}
        {...(onRetry ? { onRetry } : {})}
      />
    );
  }

  if (isLoading) {
    return <div role="status" aria-label={es.processingStatus.loading}><Skeleton className="h-24 w-full" /></div>;
  }

  const results = run?.results ?? [];

  return (
    <section
      aria-labelledby="history-heading"
      className="flex flex-col gap-3 rounded-xl border border-border bg-background p-5"
    >
      <h4 id="history-heading" className="text-lg leading-7 font-semibold text-foreground">
        {es.classification.selectionsTitle}
      </h4>
      {results.length <= 1 || results.every((result) => result.selections.length === 0) ? (
        <SelectionHistory selections={results[0]?.selections ?? []} />
      ) : (
        results.map((result, index) => {
          const headingId = `history-result-${result.id}`;
          return (
            <section key={result.id} aria-labelledby={headingId} className="flex flex-col gap-3 border-t border-border pt-4">
              <h5 id={headingId} className="text-sm font-semibold text-foreground">
                {es.classification.productHistoryHeading(
                  es.classification.productLabel(index + 1, result.product_type),
                )}
              </h5>
              <SelectionHistory selections={result.selections} />
            </section>
          );
        })
      )}
    </section>
  );
}
