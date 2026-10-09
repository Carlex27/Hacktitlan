import { useState, type PropsWithChildren } from "react";

import { ApiClientProvider, createApiClient, resolveApiBaseUrl, type ApiClient } from "@/lib/api";

export interface AppProvidersProps extends PropsWithChildren {
  /** Permite inyectar un cliente simulado en pruebas. */
  apiClient?: ApiClient;
}

export function AppProviders({ apiClient, children }: AppProvidersProps) {
  const [defaultClient] = useState(() =>
    createApiClient({ baseUrl: resolveApiBaseUrl(import.meta.env.VITE_API_BASE_URL) }),
  );
  return <ApiClientProvider client={apiClient ?? defaultClient}>{children}</ApiClientProvider>;
}
