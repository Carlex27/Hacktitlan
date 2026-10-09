import type { CertificateDetailDto, ClassificationRunDto } from "@/lib/api";

export function approvalCoverage(certificate: CertificateDetailDto | null, run: ClassificationRunDto) {
  if (!certificate || certificate.id !== run.certificate_id) return null;
  const results = new Map(run.results.map((result) => [result.product_id, result]));
  const pendingConditions = certificate.products.flatMap((product) => {
    const result = results.get(product.id);
    const candidate = result?.candidates.find((item) => item.id === result.current_selection?.candidate_id);
    if (!candidate) return [];
    const conflicts = candidate.details.conflicts;
    const hasConflicts = Array.isArray(conflicts) && conflicts.length > 0;
    const factors = candidate.factors.filter((factor) => factor.required_for_selection && ["not_matched", "conflict"].includes(factor.outcome));
    return hasConflicts || factors.length ? [{ product, hasConflicts, factors }] : [];
  });
  const pendingProducts = certificate.products.filter((product) => {
    const result = results.get(product.id);
    return !result?.current_selection || result.outcome !== "classified" || !result.fraction || !result.nico
      || !result.candidates.some((candidate) => candidate.id === result.current_selection?.candidate_id)
      || pendingConditions.some((condition) => condition.product.id === product.id);
  });
  const pendingHeats = certificate.heats.filter((heat) => {
    const products = certificate.products.filter((product) => product.heat_id === heat.id);
    return products.length === 0 || pendingProducts.some((product) => product.heat_id === heat.id);
  });
  return {
    pendingProducts,
    pendingConditions,
    pendingHeats,
    complete: certificate.products.length > 0 && pendingProducts.length === 0 && pendingHeats.length === 0
      && run.results.length === certificate.products.length
      && run.results.every((result) => certificate.products.some((product) => product.id === result.product_id)),
  };
}
