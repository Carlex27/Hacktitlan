import { LoadErrorAlert } from "@/components/feedback";
import type { CertificateDetailDto, ClassificationResultDto } from "@/lib/api";
import { es } from "@/lib/i18n";

import { CertificateSummary } from "./CertificateSummary";
import { ChemicalCompositionGrid } from "./ChemicalCompositionGrid";
import { MechanicalPropertiesByRoll } from "./MechanicalPropertiesByRoll";
import { ProductsList } from "./ProductsList";

export interface CertificateReviewTabProps {
  certificate: CertificateDetailDto | null;
  isLoading?: boolean;
  /** Falla al cargar el acta; tiene prioridad sobre el estado vacío. */
  error?: unknown;
  onRetry?: () => void;
  classificationResults?: readonly ClassificationResultDto[];
  classificationLoading?: boolean;
  classificationError?: unknown;
  onRetryClassification?: () => void;
}

export function CertificateReviewTab({
  certificate,
  isLoading,
  error = null,
  onRetry,
  classificationResults = [],
  classificationLoading = false,
  classificationError = null,
  onRetryClassification,
}: CertificateReviewTabProps) {
  if (error) {
    return (
      <LoadErrorAlert
        title={es.certificateReview.loadError}
        error={error}
        {...(onRetry ? { onRetry } : {})}
      />
    );
  }

  const loading = Boolean(isLoading);
  return (
    <>
      <CertificateSummary certificate={certificate} isLoading={loading} />
      <div className="space-y-6">
        <ChemicalCompositionGrid
          compositions={certificate?.chemical_compositions ?? []}
          isLoading={loading}
        />
        <MechanicalPropertiesByRoll certificate={certificate} isLoading={loading} />
      </div>
      <ProductsList products={certificate?.products ?? []} isLoading={loading}
        classificationResults={classificationResults} classificationLoading={classificationLoading}
        classificationError={classificationError} {...(onRetryClassification ? { onRetryClassification } : {})} />
    </>
  );
}
