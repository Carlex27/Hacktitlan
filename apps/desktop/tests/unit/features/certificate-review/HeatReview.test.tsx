import { render, screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import { HeatReview } from "@/features/certificate-review";
import { createFakeCertificate } from "../../../support/fakeBackend";

it("activa la primera colada al cargar y respeta otra selección explícita", () => {
  const base = createFakeCertificate();
  const heat = base.heats[0];
  const product = base.products[0];
  if (!heat || !product) throw new Error("Fixture incompleta");
  const certificate = { ...base, heats: [heat, { ...heat, id: 99, heat_no: "OTRA" }],
    products: [product, { ...product, id: 99, heat_id: 99, product_identifier: "ROLLO-OTRO" }] };
  const props = { certificate, isLoading: false, error: null, onRetry: vi.fn(), onSelectHeat: vi.fn(),
    classificationResults: [], classificationLoading: false, classificationError: null, onRetryClassification: vi.fn() };
  const { rerender } = render(<HeatReview {...props} certificate={null} isLoading selectedHeatId={undefined} />);
  rerender(<HeatReview {...props} selectedHeatId={undefined} />);
  expect(screen.getByRole("button", { name: `Colada: ${heat.heat_no}` })).toHaveAttribute("aria-pressed", "true");
  expect(screen.getByRole("row", { name: /PL-001/ })).toBeInTheDocument();
  expect(screen.queryByRole("row", { name: /ROLLO-OTRO/ })).not.toBeInTheDocument();
  rerender(<HeatReview {...props} selectedHeatId={99} />);
  expect(screen.getByRole("button", { name: "Colada: OTRA" })).toHaveAttribute("aria-pressed", "true");
  expect(screen.getByRole("row", { name: /ROLLO-OTRO/ })).toBeInTheDocument();
  expect(screen.queryByRole("row", { name: /PL-001/ })).not.toBeInTheDocument();
});
