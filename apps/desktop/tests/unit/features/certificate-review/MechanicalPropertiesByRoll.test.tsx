import { render, screen, within } from "@testing-library/react";
import { expect, it } from "vitest";
import { MechanicalPropertiesByRoll } from "@/features/certificate-review/components/MechanicalPropertiesByRoll";
import { createFakeCertificate } from "../../../support/fakeBackend";

it("separa ensayos por rollo y conserva los datos sin asociaciÃ³n", () => {
  const certificate = createFakeCertificate();
  const product = certificate.products[0];
  const observation = certificate.observations[0];
  if (!product || !observation) throw new Error("Fixture sin rollo o ensayo");
  render(<MechanicalPropertiesByRoll isLoading={false} certificate={{ ...certificate,
    products: [product, { ...product, id: 2, product_identifier: "R-002" }],
    observations: [observation, { ...observation, id: 30, product_id: 2, normalized_value: "999" },
      { ...observation, id: 31, product_id: null, normalized_value: "777" }],
  }} />);
  const first = within(screen.getByRole("region", { name: `Serie del rollo: ${product.product_identifier}` }));
  expect(first.getByText("310 MPa")).toBeInTheDocument();
  expect(first.queryByText("999 MPa")).not.toBeInTheDocument();
  expect(within(screen.getByRole("region", { name: "Serie del rollo: R-002" })).getByText("999 MPa")).toBeInTheDocument();
  expect(within(screen.getByRole("region", { name: "Ensayos sin rollo asociado" })).getByText("777 MPa")).toBeInTheDocument();
});
