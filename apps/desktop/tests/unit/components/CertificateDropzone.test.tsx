import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ProcessingStatusBadge } from "@/components/feedback";
import { CertificateDropzone } from "@/features/certificate-import";

import { pdfFile } from "../../support/fakeBackend";

describe("CertificateDropzone", () => {
  it("tiene nombre accesible y entrega sólo PDF", async () => {
    const user = userEvent.setup({ applyAccept: false });
    const onFilesSelected = vi.fn();
    render(<CertificateDropzone onFilesSelected={onFilesSelected} />);

    const input = screen.getByLabelText(/seleccionar certificados pdf/i);
    const png = new File([""], "foto.png", { type: "image/png" });
    await user.upload(input, [pdfFile("a.pdf"), png]);

    expect(onFilesSelected).toHaveBeenCalledWith([expect.objectContaining({ name: "a.pdf" })]);
    expect(screen.getByRole("alert")).toHaveTextContent("foto.png");
    expect(input).toHaveAttribute("aria-invalid", "true");
    expect(input.getAttribute("aria-describedby")).toContain(screen.getByRole("alert").id);
  });

  it("es alcanzable con teclado", async () => {
    const user = userEvent.setup();
    render(<CertificateDropzone onFilesSelected={vi.fn()} />);
    await user.tab();
    expect(screen.getByLabelText(/seleccionar certificados pdf/i)).toHaveFocus();
  });

  it("respeta disabled", () => {
    render(<CertificateDropzone disabled onFilesSelected={vi.fn()} />);
    expect(screen.getByLabelText(/seleccionar certificados pdf/i)).toBeDisabled();
  });
});

describe("ProcessingStatusBadge", () => {
  it.each([
    ["loading", "Procesando"],
    ["empty", "Sin datos"],
    ["success", "Extraído"],
    ["needs_review", "Requiere revisión"],
    ["error", "Error"],
  ] as const)("%s muestra %s", (status, label) => {
    render(<ProcessingStatusBadge status={status} />);
    expect(screen.getByText(label)).toHaveAttribute("data-status", status);
  });
});
