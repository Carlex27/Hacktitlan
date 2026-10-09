import { Fragment, useId, type ReactNode } from "react";
import { LoadErrorAlert } from "@/components/feedback";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import type { CertificateProductDto, ClassificationResultDto } from "@/lib/api";
import { es } from "@/lib/i18n";
import { groupProductsByHeat } from "../model/reviewRows";
import { RollCandidateSelector } from "./RollCandidateSelector";

export interface ProductsListProps {
  products: readonly CertificateProductDto[];
  isLoading?: boolean;
  classificationResults?: readonly ClassificationResultDto[];
  classificationLoading?: boolean;
  classificationError?: unknown;
  onRetryClassification?: () => void;
  renderProductDetail?: ((product: CertificateProductDto) => ReactNode) | undefined;
  activeProductId?: number | null;
  enableCandidateSelection?: boolean;
  onOpenProduct?: ((productId: number, candidateId?: number) => void) | undefined;
}

export function ProductsList({ products, isLoading = false, classificationResults = [],
  classificationLoading = false, classificationError = null, onRetryClassification,
  activeProductId, onOpenProduct, renderProductDetail, enableCandidateSelection = true }: ProductsListProps) {
  const detailId = useId();
  const text = es.workspace;
  if (isLoading) return <p role="status">{es.certificateReview.products.loadingSuggestions}</p>;
  return <section aria-label={text.reviewTitle} className="rounded-xl border border-border bg-background">
    <header className="border-b border-border p-5"><h3 className="text-lg font-semibold">{text.reviewTitle}</h3>
      <p className="mt-1 text-sm text-muted-foreground">{renderProductDetail ? text.selectRoll : text.alternatives}</p></header>
    {Boolean(classificationError) && <div className="px-4 pb-4"><LoadErrorAlert title={es.classification.loadError}
      error={classificationError} {...(onRetryClassification ? { onRetry: onRetryClassification } : {})} /></div>}
    {classificationLoading && <p role="status" className="px-4 pb-4">{es.certificateReview.products.loadingSuggestions}</p>}
    {products.length === 0 ? <p className="p-4 text-muted-foreground">{es.certificateReview.products.emptyTitle}</p> :
      <div className="overflow-x-auto focus-visible:outline-2 focus-visible:outline-primary" tabIndex={0} role="region" aria-label={text.reviewTitle}><table className="w-full min-w-[52rem] text-left text-sm leading-6">
        <caption className="sr-only">{text.reviewTitle}</caption>
        <thead className="border-b border-border bg-muted/60 text-foreground"><tr>
          {[text.fraction, text.nico, text.serial, text.description, text.dimensions, text.state, text.detail].map((label) =>
            <th key={label} scope="col" className="whitespace-nowrap px-4 py-3 text-xs font-semibold">{label}</th>)}
        </tr></thead>
        {groupProductsByHeat(products).map(([heatId, group]) => <tbody key={heatId ?? "unknown"}>
          {group.map((product) => {
            const result = classificationResults.find((value) => value.product_id === product.id);
            const candidate = result?.candidates.find((value) => value.id === result.current_selection?.candidate_id) ?? result?.candidates[0];
            const identifier = product.product_identifier ?? product.label_no ?? `#${product.id}`;
            return <Fragment key={product.id}><tr onClick={(event) => {
              if (event.target instanceof HTMLElement && !event.target.closest("button,select,option")) onOpenProduct?.(product.id);
            }} className={`border-t border-border ${onOpenProduct ? "cursor-pointer " : ""}${activeProductId === product.id ? "bg-accent" : "hover:bg-muted/40"}`}>
              <td className="min-w-28 whitespace-nowrap px-4 py-3 tabular-nums font-medium">{candidate?.fraction ?? result?.fraction ?? text.unknown}</td>
              <td className="px-4 py-3">
                {candidate && onOpenProduct && enableCandidateSelection && !renderProductDetail ? <RollCandidateSelector candidates={result?.candidates ?? []} current={candidate} identifier={identifier}
                  disabled={!onOpenProduct || classificationLoading} onSelect={(candidateId) => onOpenProduct?.(product.id, candidateId)} />
                  : <span>{classificationLoading ? es.processingStatus.loading : candidate ? `NICO ${candidate.nico}` : text.noCandidates}</span>}
              </td>
              <td className="min-w-36 whitespace-nowrap px-4 py-3 font-medium">{identifier}</td>
              <td className="max-w-64 px-4 py-3">{result?.description ?? candidate?.description ?? product.product_type ?? text.unknown}</td>
              <td className="whitespace-nowrap px-4 py-3 tabular-nums">{product.thickness_mm ?? text.unknown} × {product.width_mm ?? text.unknown}</td>
              <td className="min-w-32 px-4 py-3"><Badge variant="secondary" className={`h-auto min-h-7 whitespace-normal px-3 py-1 ${result?.outcome === "needs_review" || (!result?.current_selection && !candidate) ? "border-warning-border bg-warning-background text-warning-foreground" : ""}`}>{result?.outcome === "needs_review" ? text.needsReview : result?.current_selection ? text.selected : candidate ? text.suggested : text.needsReview}</Badge></td>
              <td className="px-4 py-3">{onOpenProduct && <Button className="min-h-11" id={`roll-${product.id}`} variant="outline" onClick={() => onOpenProduct(product.id)}
                aria-label={`${text.detail}: ${identifier}`} aria-expanded={activeProductId === product.id} aria-controls={renderProductDetail && activeProductId === product.id ? detailId : undefined}>{activeProductId === product.id && renderProductDetail ? text.closeDetail : text.detail}</Button>}</td>
            </tr>
            {renderProductDetail && activeProductId === product.id && <tr><td colSpan={7} className="border-t border-border bg-muted/20 p-5">
              <section id={detailId} aria-label={`${text.detail}: ${identifier}`} className="space-y-6 whitespace-normal">{renderProductDetail(product)}</section>
            </td></tr>}
            </Fragment>;
          })}
        </tbody>)}
      </table></div>}
  </section>;
}
