import { useCallback, useEffect, useState } from "react";

import {
  getCertificate,
  useApiClient,
  type ApiError,
  type CertificateDetailDto,
} from "@/lib/api";

export interface UseCertificateResult {
  certificate: CertificateDetailDto | null;
  isLoading: boolean;
  error: ApiError | null;
  reload: () => void;
}

interface CertificateState {
  certificateId: number | null;
  version: number;
  certificate: CertificateDetailDto | null;
  error: ApiError | null;
}

export function useCertificate(certificateId: number | null): UseCertificateResult {
  const api = useApiClient();
  const [version, setVersion] = useState(0);
  const [state, setState] = useState<CertificateState>({
    certificateId: null,
    version: 0,
    certificate: null,
    error: null,
  });

  const reload = useCallback(() => {
    setVersion((v) => v + 1);
  }, []);

  useEffect(() => {
    if (certificateId === null) return;

    const controller = new AbortController();
    let isCurrent = true;

    getCertificate(api, certificateId, { signal: controller.signal })
      .then((cert) => {
        if (!isCurrent) return;
        setState({
          certificateId,
          version,
          certificate: cert,
          error: null,
        });
      })
      .catch((err: unknown) => {
        if (!isCurrent || controller.signal.aborted) return;
        setState({
          certificateId,
          version,
          certificate: null,
          error: err as ApiError,
        });
      });

    return () => {
      isCurrent = false;
      controller.abort();
    };
  }, [api, certificateId, version]);

  const isMatched =
    certificateId !== null &&
    state.certificateId === certificateId &&
    state.version === version;

  const certificate = isMatched ? state.certificate : null;
  const isLoading = certificateId !== null && !isMatched;
  const error = isMatched ? state.error : null;

  return { certificate, isLoading, error, reload };
}
