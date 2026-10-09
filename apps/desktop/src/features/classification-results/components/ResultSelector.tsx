import { ProcessingStatusBadge } from "@/components/feedback";
import type { ClassificationResultDto } from "@/lib/api";
import { es } from "@/lib/i18n";
import { cn } from "@/lib/utils";

import { formatTariffCode, outcomeToProcessingStatus } from "../model";

export interface ResultSelectorProps {
  results: readonly ClassificationResultDto[];
  activeResultId: number | null;
  onSelect(resultId: number): void;
}

/** Lista de productos de la ejecución; cada uno se revisa por separado. */
export function ResultSelector({ results, activeResultId, onSelect }: ResultSelectorProps) {
  return (
    <section
      aria-labelledby="result-selector-heading"
      className="flex flex-col gap-2 rounded-lg border border-slate-200 bg-white p-3 shadow-sm"
    >
      <h4 id="result-selector-heading" className="text-xs font-bold text-slate-800">
        {es.classification.productsTitle} ({results.length})
      </h4>
      <ul className="flex flex-wrap gap-2">
        {results.map((result, index) => {
          const isActive = result.id === activeResultId;
          return (
            <li key={result.id}>
              <button
                type="button"
                aria-pressed={isActive}
                onClick={() => onSelect(result.id)}
                className={cn(
                  "flex flex-col items-start gap-1 rounded-md border px-2.5 py-1.5 text-left text-xs transition-colors",
                  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500",
                  isActive
                    ? "border-blue-400 bg-blue-50/70 ring-1 ring-blue-400"
                    : "border-slate-200 bg-white hover:bg-slate-50",
                )}
              >
                <span className="font-semibold text-slate-800">
                  {es.classification.productLabel(index + 1, result.product_type)}
                </span>
                <span className="flex items-center gap-2">
                  <span className="font-mono text-[11px] text-slate-700">
                    {formatTariffCode(result.fraction, result.nico)}
                  </span>
                  <ProcessingStatusBadge status={outcomeToProcessingStatus(result.outcome)} />
                </span>
              </button>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
