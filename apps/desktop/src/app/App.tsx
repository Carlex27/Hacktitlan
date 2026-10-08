import { AppShell } from "@/components/layout";
import { ConnectionGate } from "@/features/connection-status";
import type { ApiClient } from "@/lib/api";
import { ImportCertificatePage } from "@/pages";

import { AppProviders } from "./providers/AppProviders";

export interface AppProps {
  apiClient?: ApiClient;
}

export function App({ apiClient }: AppProps) {
  return (
    <AppProviders {...(apiClient ? { apiClient } : {})}>
      <AppShell>
        <ConnectionGate>
          <ImportCertificatePage />
        </ConnectionGate>
      </AppShell>
    </AppProviders>
  );
}
