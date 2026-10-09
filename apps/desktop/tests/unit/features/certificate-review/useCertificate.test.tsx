import type { PropsWithChildren } from "react";
import { act, renderHook, waitFor } from "@testing-library/react";
import { expect, it } from "vitest";
import { ApiClientProvider } from "@/lib/api";
import { useCertificate } from "@/features/certificate-review";
import { createFakeBackend, createFakeCertificate, envelope } from "../../../support/fakeBackend";

it("reutiliza el detalle al volver al acta y fuerza datos nuevos al recargar", async () => {
  let certificate = createFakeCertificate();
  const backend = createFakeBackend({
    "GET /api/v1/certificates/42": () => envelope(certificate),
  });
  const wrapper = ({ children }: PropsWithChildren) => (
    <ApiClientProvider client={backend.client}>{children}</ApiClientProvider>
  );
  const first = renderHook(() => useCertificate(42), { wrapper });
  await waitFor(() => expect(first.result.current.isLoading).toBe(false));
  first.unmount();
  const second = renderHook(() => useCertificate(42), { wrapper });
  await waitFor(() => expect(second.result.current.isLoading).toBe(false));
  expect(backend.calls).toHaveLength(1);
  certificate = { ...certificate, certificate_no: "ACTA-ACTUALIZADA" };
  act(() => second.result.current.reload());
  await waitFor(() => expect(second.result.current.certificate?.certificate_no).toBe("ACTA-ACTUALIZADA"));
  expect(backend.calls).toHaveLength(2);
});
