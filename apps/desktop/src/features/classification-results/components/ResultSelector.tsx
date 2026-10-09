import { useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ProcessingStatusBadge } from "@/components/feedback";
import type { CertificateProductDto, ClassificationResultDto } from "@/lib/api";
import { es } from "@/lib/i18n";
import { cn } from "@/lib/utils";

import { formatTariffCode, outcomeToProcessingStatus } from "../model";

export interface ResultSelectorProps {
  products?: readonly CertificateProductDto[];
  results: readonly ClassificationResultDto[];
  activeResultId: number | null;
  onSelect(resultId: number): void;
}

/** Lista de productos de la ejecución; cada uno se revisa por separado. */
export function ResultSelector({ products = [], results, activeResultId, onSelect }: ResultSelectorProps) {
  const [page, setPage] = useState(() => Math.floor(Math.max(0, results.findIndex((result) => result.id === activeResultId)) / 10));
  const pageCount = Math.max(1, Math.ceil(results.length / 10));
  const currentPage = Math.min(page, pageCount - 1);
  const start = currentPage * 10;
  return (
    <section
      aria-labelledby="result-selector-heading"
      className="flex flex-col gap-2 rounded-xl border border-border bg-background p-5"
    >
      <h4 id="result-selector-heading" className="text-lg leading-7 font-semibold text-foreground">
        {es.classification.productsTitle} ({results.length})
      </h4>
      <ul className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-5">
        {results.slice(start, start + 10).map((result, index) => {
          const isActive = result.id === activeResultId;
          return (
            <li key={result.id}>
              <button
                type="button"
                aria-pressed={isActive}
                onClick={() => onSelect(result.id)}
                className={cn(
                  "flex min-h-20 w-full flex-col items-start gap-2 rounded-lg border px-4 py-3 text-left text-sm transition-colors",
                  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary",
                  isActive
                    ? "border-primary bg-accent ring-1 ring-primary"
                    : "border-border bg-background hover:bg-muted/40",
                )}
              >
                <span className="font-semibold text-foreground">
                  {products.find((product) => product.id === result.product_id)?.product_identifier ?? es.classification.productLabel(start + index + 1, result.product_type)}
                </span>
                <span className="flex flex-wrap items-center gap-2">
                  <span className="tabular-nums text-sm text-foreground">
                    {formatTariffCode(result.fraction, result.nico)}
                  </span>
                  {result.current_selection && result.outcome === "classified" ?
                    <Badge>{es.classification.confirmed}</Badge> :
                    <ProcessingStatusBadge status={outcomeToProcessingStatus(result.outcome)} />}
                </span>
              </button>
            </li>
          );
        })}
      </ul>
      {pageCount > 1 && <nav aria-label={es.classification.productsPagination} className="mt-2 flex items-center justify-end gap-3">
        <Button variant="outline" className="size-11" aria-label={es.classification.previousPage}
          disabled={currentPage === 0} onClick={() => setPage(currentPage - 1)}>
          <ChevronLeft aria-hidden="true" />
        </Button>
        <span role="status" className="text-sm text-muted-foreground tabular-nums">
          {es.classification.pageOf(currentPage + 1, pageCount)}
        </span>
        <Button variant="outline" className="size-11" aria-label={es.classification.nextPage}
          disabled={currentPage === pageCount - 1} onClick={() => setPage(currentPage + 1)}>
          <ChevronRight aria-hidden="true" />
        </Button>
      </nav>}
    </section>
  );
}
