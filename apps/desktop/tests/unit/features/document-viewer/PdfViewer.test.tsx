import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ApiClientProvider } from "@/lib/api";
import { PdfViewer } from "@/features/document-viewer";
import { createFakeBackend, pdfResponse } from "../../../support/fakeBackend";

describe("Documento original", () => {
  it("recreates the PDF frame when navigating to another page without downloading again", async () => {
    const path = "/api/v1/documents/10/file";
    const backend = createFakeBackend({ [`GET ${path}`]: () => pdfResponse("ligie.pdf") });
    const view = (page: number) => <ApiClientProvider client={backend.client}><PdfViewer filePath={path} page={page} /></ApiClientProvider>;
    const { container, rerender } = render(view(24));
    await waitFor(() => expect(container.querySelector("iframe")).toHaveAttribute("src", expect.stringContaining("#page=24")));
    const first = container.querySelector("iframe");
    rerender(view(31));
    expect(container.querySelector("iframe")).not.toBe(first);
    expect(container.querySelector("iframe")).toHaveAttribute("src", expect.stringContaining("#page=31"));
    rerender(view(24));
    expect(container.querySelector("iframe")).toHaveAttribute("src", expect.stringContaining("#page=24"));
    expect(backend.calls.filter((call) => call === `GET ${path}`)).toHaveLength(1);
  });
  it("ofrece el original Excel sin tratar sus bytes como PDF", async () => {
    const backend = createFakeBackend({ "GET /api/v1/documents/10/file": () => new Response("xlsx", {
      headers: { "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" },
    }) });
    const { container } = render(<ApiClientProvider client={backend.client}><PdfViewer filePath="/api/v1/documents/10/file" /></ApiClientProvider>);
    expect(await screen.findByRole("link", { name: "Descargar documento original" })).toHaveAttribute("href", "http://backend.test/api/v1/documents/10/file");
    expect(container.querySelector("iframe")).toBeNull();
  });
});
