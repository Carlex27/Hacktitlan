import type { CertificateDetailDto, CertificateProductDto } from "@/lib/api";

export function groupProductsByHeat(products: readonly CertificateProductDto[]) {
  const groups = new Map<number | null, CertificateProductDto[]>();
  for (const product of products) {
    const group = groups.get(product.heat_id) ?? [];
    group.push(product);
    groups.set(product.heat_id, group);
  }
  return [...groups.entries()];
}

export function scopeCertificateToProduct(certificate: CertificateDetailDto, product: CertificateProductDto): CertificateDetailDto {
  return { ...certificate, products: [product],
    heats: certificate.heats.filter((heat) => heat.id === product.heat_id),
    observations: certificate.observations.filter((value) => value.product_id === product.id ||
      (value.product_id === null && (value.heat_id === null || value.heat_id === product.heat_id))),
    chemical_compositions: certificate.chemical_compositions.filter((value) => value.product_id === product.id ||
      (value.product_id === null && (value.heat_id === null || value.heat_id === product.heat_id))),
  };
}

export function scopeCertificateToHeat(certificate: CertificateDetailDto, heatId: number | null): CertificateDetailDto {
  const products = certificate.products.filter((product) => product.heat_id === heatId);
  const productIds = new Set(products.map((product) => product.id));
  return { ...certificate, products,
    heats: certificate.heats.filter((heat) => heat.id === heatId),
    observations: certificate.observations.filter((value) => value.product_id !== null
      ? productIds.has(value.product_id) : value.heat_id === heatId),
    chemical_compositions: certificate.chemical_compositions.filter((value) => value.product_id !== null
      ? productIds.has(value.product_id) : value.heat_id === heatId),
  };
}
