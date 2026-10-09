import { describe, expect, it } from "vitest";
import { groupProductsByHeat, scopeCertificateToProduct, scopeCertificateToHeat } from "@/features/certificate-review/model/reviewRows";
import { createFakeCertificate } from "../../../support/fakeBackend";

describe("Datos del rollo", () => {
  it("agrupa cantidades variables y conserva los rollos sin colada", () => {
    const product = createFakeCertificate().products[0];
    if (!product) throw new Error("Fixture incompleta");
    expect(groupProductsByHeat([product, { ...product, id: 2, heat_id: null }, { ...product, id: 3 }])
      .map(([heatId, rows]) => [heatId, rows.map((row) => row.id)])).toEqual([[product.heat_id, [1, 3]], [null, [2]]]);
  });
  it("no mezcla observaciones de otros rollos, conserva datos compartidos y los valores cero y false", () => {
    const base = createFakeCertificate();
    const product = base.products[0];
    const observation = base.observations[0];
    if (!product || !observation) throw new Error("Fixture incompleta");
    const certificate = { ...base, observations: [
      { ...observation, id: 1, product_id: product.id, normalized_value: 0 },
      { ...observation, id: 2, product_id: 99 },
      { ...observation, id: 3, product_id: null, heat_id: product.heat_id, normalized_value: false },
      { ...observation, id: 4, product_id: null, heat_id: 999 },
    ] };
    const scoped = scopeCertificateToProduct(certificate, product);
    expect(scoped.observations.map((value) => value.normalized_value)).toEqual([0, false]);
    expect(scoped.products).toEqual([product]);
    expect(certificate.observations).toHaveLength(4);
  });
});

it("seleccionar colada no mezcla datos de otra colada ni atribuye datos globales", () => {
  const certificate = createFakeCertificate();
  const product = certificate.products[0];
  const observation = certificate.observations[0];
  if (!product || !observation) throw new Error("Fixture incompleta");
  const scoped = scopeCertificateToHeat({ ...certificate,
    products: [product, { ...product, id: 2, heat_id: 99 }],
    observations: [observation, { ...observation, id: 2, product_id: 2 },
      { ...observation, id: 3, product_id: null, heat_id: product.heat_id },
      { ...observation, id: 4, product_id: null, heat_id: null }],
  }, product.heat_id);
  expect(scoped.products.map((item) => item.id)).toEqual([product.id]);
  expect(scoped.observations.map((item) => item.id)).toEqual([observation.id, 3]);
});
