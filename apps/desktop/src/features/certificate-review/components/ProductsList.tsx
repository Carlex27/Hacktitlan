import { Fragment, useId, type ReactNode } from "react";
import { LoadErrorAlert } from "@/components/feedback";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import type { CertificateProductDto, CertificateHeatDto, ClassificationResultDto } from "@/lib/api";
import { es } from "@/lib/i18n";
import { groupProductsByHeat } from "../model/reviewRows";
import { RollCandidateSelector } from "./RollCandidateSelector";

export interface ProductsListProps {
  products: readonly CertificateProductDto[];
  isLoading?: boolean;
  heats?: readonly CertificateHeatDto[];
  classificationResults?: readonly ClassificationResultDto[];
  classificationLoading?: boolean;
  classificationError?: unknown;
  onRetryClassification?: () => void;
  renderProductDetail?: ((product: CertificateProductDto) => ReactNode) | undefined;
  activeProductId?: number | null;
  enableCandidateSelection?: boolean;
  onOpenProduct?: ((productId: number, candidateId?: number) => void) | undefined;
}

export function ProductsList({ products, isLoading = false, heats = [], classificationResults = [],
  classificationLoading = false, classificationError = null, onRetryClassification,
  activeProductId, onOpenProduct, renderProductDetail, enableCandidateSelection = true }: ProductsListProps) {
  const detailId = useId();
  const text = es.workspace;
  if (isLoading) return <p role="status">{es.certificateReview.products.loadingSuggestions}</p>;
  return <section aria-label={text.reviewTitle} className="rounded-xl border border-border bg-background">
    <header className="p-4"><h3 className="text-lg font-semibold">{text.reviewTitle}</h3>
      <p className="mt-1 text-sm text-muted-foreground">{renderProductDetail ? text.selectRoll : text.alternatives}</p></header>
    {Boolean(classificationError) && <div className="px-4 pb-4"><LoadErrorAlert title={es.classification.loadError}
      error={classificationError} {...(onRetryClassification ? { onRetry: onRetryClassification } : {})} /></div>}
    {classificationLoading && <p role="status" className="px-4 pb-4">{es.certificateReview.products.loadingSuggestions}</p>}
    {products.length === 0 ? <p className="p-4 text-muted-foreground">{es.certificateReview.products.emptyTitle}</p> :
      <div className="overflow-x-auto focus-visible:outline-2 focus-visible:outline-primary" tabIndex={0} role="region" aria-label={text.reviewTitle}><table className="w-full min-w-[64rem] text-left text-sm leading-6">
        <caption className="sr-only">{text.reviewTitle}</caption>
        <thead className="border-y border-border bg-muted/40 text-muted-foreground"><tr>
          {[text.fraction, text.nico, text.serial, text.description, text.dimensions, text.state, text.detail].map((label) =>
            <th key={label} scope="col" className="whitespace-nowrap px-4 py-3 font-medium">{label}</th>)}
        </tr></thead>
        {groupProductsByHeat(products).map(([heatId, group]) => <tbody key={heatId ?? "unknown"}>
          <tr className="bg-muted/40"><th scope="rowgroup" colSpan={7} className="px-4 py-2 font-medium text-foreground">
            {text.heat}: {heats.find((heat) => heat.id === heatId)?.heat_no ?? text.unknownHeat}
          </th></tr>
          {group.map((product) => {
            const result = classificationResults.find((value) => value.product_id === product.id);
            const candidate = result?.candidates.find((value) => value.id === result.current_selection?.candidate_id) ?? result?.candidates[0];
            const identifier = product.product_identifier ?? product.label_no ?? `#${product.id}`;
            return <Fragment key={product.id}><tr onClick={(event) => {
              if (event.target instanceof HTMLElement && !event.target.closest("button,select,option")) onOpenProduct?.(product.id);
            }} className={`border-t border-border ${onOpenProduct ? "cursor-pointer " : ""}${activeProductId === product.id ? "bg-accent" : "hover:bg-muted/40"}`}>
              <td className="min-w-28 whitespace-nowrap px-4 py-4 tabular-nums font-medium">{candidate?.fraction ?? result?.fraction ?? text.unknown}</td>
              <td className="px-4 py-4">
                {candidate && onOpenProduct && enableCandidateSelection && !renderProductDetail ? <RollCandidateSelector candidates={result?.candidates ?? []} current={candidate} identifier={identifier}
                  disabled={!onOpenProduct || classificationLoading} onSelect={(candidateId) => onOpenProduct?.(product.id, candidateId)} />
                  : <span>{classificationLoading ? es.processingStatus.loading : candidate ? `NICO ${candidate.nico}` : text.noCandidates}</span>}
              </td>
              <td className="min-w-44 whitespace-nowrap px-4 py-4 font-medium">{identifier}</td>
              <td className="max-w-64 px-4 py-4">{result?.description ?? candidate?.description ?? product.product_type ?? text.unknown}</td>
              <td className="whitespace-nowrap px-4 py-4 tabular-nums">{product.thickness_mm ?? text.unknown} × {product.width_mm ?? text.unknown}</td>
              <td className="min-w-40 px-4 py-4"><Badge variant="secondary" className="h-auto whitespace-normal py-1">{result?.outcome === "needs_review" ? text.needsReview : result?.current_selection ? text.selected : candidate ? text.suggested : text.needsReview}</Badge></td>
              <td className="px-4 py-4">{onOpenProduct && <Button className="min-h-10" id={`roll-${product.id}`} variant="outline" onClick={() => onOpenProduct(product.id)}
                aria-label={`${text.detail}: ${identifier}`} aria-expanded={activeProductId === product.id} aria-controls={renderProductDetail && activeProductId === product.id ? detailId : undefined}>{activeProductId === product.id && renderProductDetail ? text.closeDetail : text.detail}</Button>}</td>
            </tr>
            {renderProductDetail && activeProductId === product.id && <tr><td colSpan={7} className="border-t border-border p-4">
              <section id={detailId} aria-label={`${text.detail}: ${identifier}`} className="space-y-6">{renderProductDetail(product)}</section>
            </td></tr>}
            </Fragment>;
          })}
        </tbody>)}
      </table></div>}
  </section>;
}
