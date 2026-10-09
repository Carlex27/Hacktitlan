import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { LoadErrorAlert } from "@/components/feedback";
import { ClassificationValidationTab, type ClassificationValidationTabProps } from "@/features/classification-results";
import type { CertificateDetailDto } from "@/lib/api";
import { es } from "@/lib/i18n";
import { scopeCertificateToProduct } from "../model/reviewRows";
import { CertificateSummary } from "./CertificateSummary";
import { ProductsList } from "./ProductsList";
import { ChemicalCompositionGrid } from "./ChemicalCompositionGrid";
import { MechanicalPropertiesGrid } from "./MechanicalPropertiesGrid";
import { ProductDetails } from "./ProductDetails";
import { ExtractedObservations } from "./ExtractedObservations";

interface RollReviewProps extends ClassificationValidationTabProps {
  certificate: CertificateDetailDto | null;
  certificateLoading: boolean;
  certificateError: unknown;
  onRetryCertificate(): void;
}

export function RollReview({ certificate, certificateLoading, certificateError, onRetryCertificate, ...classification }: RollReviewProps) {
  const [selection, setSelection] = useState<{ productId: number; candidateId: number | null } | null>(null);
  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => { if (selection) heading.current?.focus(); }, [selection]);
  if (certificateError) return <LoadErrorAlert title={es.certificateReview.loadError} error={certificateError} onRetry={onRetryCertificate} />;
  const product = certificate?.products.find((value) => value.id === selection?.productId);
  const scoped = certificate && product ? scopeCertificateToProduct(certificate, product) : null;
  const result = classification.run?.results.find((value) => value.product_id === product?.id);
  return <>
    <CertificateSummary certificate={certificate} isLoading={certificateLoading} />
    <ProductsList products={certificate?.products ?? []} heats={certificate?.heats ?? []}
      isLoading={certificateLoading} classificationResults={classification.run?.results ?? []}
      classificationLoading={Boolean(classification.isLoading)} classificationError={classification.error}
      onRetryClassification={classification.onReloadRun} activeProductId={selection?.productId ?? null}
      onOpenProduct={(productId, candidateId) => setSelection({ productId, candidateId: candidateId ?? null })} />
    {scoped && product && <section aria-labelledby="roll-detail-title" className="space-y-6">
      <header className="flex flex-wrap items-center justify-between gap-3 border-b border-border pb-4">
        <h2 ref={heading} tabIndex={-1} id="roll-detail-title" className="text-lg font-semibold focus-visible:outline-2 focus-visible:outline-primary">
          {es.workspace.detail}: {product.product_identifier ?? product.label_no ?? `#${product.id}`}
        </h2><Button className="min-h-10" variant="outline" onClick={() => { document.getElementById(`roll-${product.id}`)?.focus(); setSelection(null); }}>{es.workspace.closeDetail}</Button>
      </header>
      <ProductDetails product={product} heat={scoped.heats[0]} />
      <div className="grid gap-6 xl:grid-cols-2"><ChemicalCompositionGrid compositions={scoped.chemical_compositions} />
        <MechanicalPropertiesGrid observations={scoped.observations} /></div>
      <ExtractedObservations observations={scoped.observations} />
      {result ? <ClassificationValidationTab {...classification} resultId={result.id} initialCandidateId={selection?.candidateId ?? null} /> :
        <p role="status">{classification.isLoading ? es.processingStatus.loading : es.workspace.noCandidates}</p>}
    </section>}
  </>;
}
