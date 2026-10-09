import { useState } from "react";
import { LoadErrorAlert } from "@/components/feedback";
import { Button } from "@/components/ui/button";
import type { CertificateDetailDto, ClassificationResultDto } from "@/lib/api";
import { es } from "@/lib/i18n";
import { scopeCertificateToProduct, scopeCertificateToHeat } from "../model/reviewRows";
import { CertificateSummary } from "./CertificateSummary";
import { ChemicalCompositionGrid } from "./ChemicalCompositionGrid";
import { MechanicalPropertiesGrid } from "./MechanicalPropertiesGrid";
import { ProductsList } from "./ProductsList";
import { ProductDetails } from "./ProductDetails";
import { ExtractedObservations } from "./ExtractedObservations";

export interface HeatReviewProps {
  certificate: CertificateDetailDto | null;
  isLoading: boolean;
  error: unknown;
  onRetry(): void;
  selectedHeatId: number | null | undefined;
  onSelectHeat(heatId: number | null): void;
  detailed?: boolean;
  classificationResults: readonly ClassificationResultDto[];
  classificationLoading: boolean;
  classificationError: unknown;
  onRetryClassification(): void;
  onShowExtracted?: () => void;
}

export function HeatReview({ certificate, isLoading, error, onRetry, selectedHeatId, onSelectHeat, detailed = false,
  classificationResults, classificationLoading, classificationError, onRetryClassification, onShowExtracted }: HeatReviewProps) {
  const [selectedProductId, setSelectedProductId] = useState<number | null>(null);
  if (error) return <LoadErrorAlert title={es.certificateReview.loadError} error={error} onRetry={onRetry} />;
  const activeHeatId = selectedHeatId === undefined ? certificate?.heats[0]?.id : selectedHeatId;
  const scoped = certificate && activeHeatId !== undefined ? scopeCertificateToHeat(certificate, activeHeatId) : null;
  const information = scoped && !isLoading && <section aria-label={es.workspace.heatInformation}>
    <ProductsList products={scoped.products} classificationResults={classificationResults}
      classificationLoading={classificationLoading} classificationError={classificationError} onRetryClassification={onRetryClassification}
      activeProductId={detailed ? selectedProductId : null}
      enableCandidateSelection={false}
      onOpenProduct={detailed || onShowExtracted ? (id) => {
        setSelectedProductId((current) => detailed && current === id ? null : id);
        if (!detailed) onShowExtracted?.();
      } : undefined}
      renderProductDetail={detailed ? (product) => {
        const roll = scopeCertificateToProduct(scoped, product);
        return <>
          <ProductDetails product={product} heat={roll.heats[0]} />
          <ChemicalCompositionGrid compositions={roll.chemical_compositions} />
          <MechanicalPropertiesGrid observations={roll.observations} />
          <ExtractedObservations observations={roll.observations} products={roll.products} />
        </>;
      } : undefined} />
  </section>;
  const heats = certificate?.heats.map((heat) => ({ id: heat.id as number | null, label: `${es.workspace.batch}: ${heat.heat_no ?? `#${heat.id}`}` })) ?? [];
  if (certificate && (certificate.products.some((product) => product.heat_id === null)
    || certificate.observations.some((value) => value.heat_id === null && value.product_id === null)
    || certificate.chemical_compositions.some((value) => value.heat_id === null && value.product_id === null))) {
    heats.push({ id: null, label: es.workspace.unknownHeat });
  }
  return <>
    <CertificateSummary certificate={certificate} isLoading={isLoading} />
    {!isLoading && certificate && <section aria-label={es.workspace.heatsTitle} className="space-y-3">
      <h2 className="text-lg font-semibold">{es.workspace.heatsTitle}</h2>
      <div className="flex flex-wrap gap-3">
        {heats.map((heat) => <div key={heat.id ?? "unassigned"} >
          <Button variant={activeHeatId === heat.id ? "default" : "outline"}
            className="min-h-11"
            aria-pressed={activeHeatId === heat.id} onClick={() => { setSelectedProductId(null); onSelectHeat(heat.id); }}>
            {heat.label}
          </Button>
        </div>)}
      </div>
      {!scoped && <p role="status" className="text-muted-foreground">{heats.length ? es.workspace.selectHeat : es.workspace.noHeats}</p>}
    </section>}
    {information}
  </>;
}
