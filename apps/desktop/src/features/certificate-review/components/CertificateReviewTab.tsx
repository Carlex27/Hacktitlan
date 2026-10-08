import { LoadErrorAlert } from "@/components/feedback";
import type { CertificateDetailDto } from "@/lib/api";
import { es } from "@/lib/i18n";

import { CertificateSummary } from "./CertificateSummary";
import { ChemicalCompositionGrid } from "./ChemicalCompositionGrid";
import { MechanicalPropertiesGrid } from "./MechanicalPropertiesGrid";
import { ProductsList } from "./ProductsList";

export interface CertificateReviewTabProps {
  certificate: CertificateDetailDto | null;
  isLoading?: boolean;
  /** Falla al cargar el acta; tiene prioridad sobre el estado vacío. */
  error?: unknown;
  onRetry?: () => void;
}

export function CertificateReviewTab({
  certificate,
  isLoading,
  error = null,
  onRetry,
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
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
        <ChemicalCompositionGrid
          compositions={certificate?.chemical_compositions ?? []}
          isLoading={loading}
        />
        <MechanicalPropertiesGrid
          observations={certificate?.observations ?? []}
          isLoading={loading}
        />
      </div>
      <ProductsList products={certificate?.products ?? []} isLoading={loading} />
    </>
  );
}
