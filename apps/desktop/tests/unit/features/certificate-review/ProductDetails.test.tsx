import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ProductDetails } from "@/features/certificate-review/components/ProductDetails";
import { createFakeCertificate } from "../../../support/fakeBackend";

describe("Detalle del producto", () => {
  it("explica códigos conocidos y conserva false, cero y códigos desconocidos", () => {
    const product = createFakeCertificate().products[0];
    if (!product) throw new Error("Fixture incompleta");
    render(<ProductDetails product={{ ...product, rolling: "cold", form: "forma_no_catalogada", coiled: false, weight_kg: "0" }} heat={undefined} />);
    expect(screen.getByText("Laminado en frío")).toBeInTheDocument();
    expect(screen.getByText("forma_no_catalogada")).toBeInTheDocument();
    expect(screen.getByText("Sin enrollar")).toBeInTheDocument();
    expect(screen.getByText("0")).toBeInTheDocument();
  });
});
