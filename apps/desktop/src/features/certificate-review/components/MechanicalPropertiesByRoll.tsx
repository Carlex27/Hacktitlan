import type { CertificateDetailDto } from "@/lib/api";
import { es } from "@/lib/i18n";
import { extractMechanicalProperties } from "../model";
import { MechanicalPropertiesGrid } from "./MechanicalPropertiesGrid";

export function MechanicalPropertiesByRoll({ certificate, isLoading }: { certificate: CertificateDetailDto | null; isLoading: boolean }) {
  if (isLoading || !certificate) return <MechanicalPropertiesGrid observations={[]} isLoading={isLoading} />;
  const unassigned = certificate.observations.filter((observation) =>
    !certificate.products.some((product) => product.id === observation.product_id));
  return <div className="space-y-6">
    {certificate.products.map((product) => <section key={product.id} aria-label={`${es.workspace.serial}: ${product.product_identifier ?? product.label_no ?? `#${product.id}`}`} className="space-y-2">
      <h3 className="text-lg font-semibold">{es.workspace.serial}: {product.product_identifier ?? product.label_no ?? `#${product.id}`}</h3>
      <MechanicalPropertiesGrid observations={certificate.observations.filter((observation) => observation.product_id === product.id)} />
    </section>)}
    {extractMechanicalProperties(unassigned).length > 0 && <section aria-label={es.certificateReview.mechanics.unassigned} className="space-y-2">
      <h3 className="text-lg font-semibold">{es.certificateReview.mechanics.unassigned}</h3>
      <p className="text-sm text-muted-foreground">{es.certificateReview.mechanics.unassignedDescription}</p>
      <MechanicalPropertiesGrid observations={unassigned} />
    </section>}
    {certificate.products.length === 0 && extractMechanicalProperties(unassigned).length === 0 && <MechanicalPropertiesGrid observations={[]} />}
  </div>;
}
