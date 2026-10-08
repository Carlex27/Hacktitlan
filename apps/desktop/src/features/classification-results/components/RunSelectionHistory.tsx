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
    return <Skeleton className="h-24 w-full" />;
  }

  const results = run?.results ?? [];

  return (
    <section
      aria-labelledby="history-heading"
      className="flex flex-col gap-3 rounded-lg border border-slate-200 bg-white p-3.5 shadow-sm"
    >
      <h4 id="history-heading" className="text-xs font-bold text-slate-800">
        {es.classification.selectionsTitle}
      </h4>
      {results.length <= 1 ? (
        <SelectionHistory selections={results[0]?.selections ?? []} />
      ) : (
        results.map((result, index) => {
          const headingId = `history-result-${result.id}`;
          return (
            <section key={result.id} aria-labelledby={headingId} className="flex flex-col gap-2">
              <h5 id={headingId} className="text-[11px] font-semibold text-slate-700">
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
