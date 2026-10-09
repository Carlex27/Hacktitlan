import type { PropsWithChildren } from "react";

import { ApiClientContext } from "./apiClientContext";
import type { ApiClient } from "./client";

export interface ApiClientProviderProps extends PropsWithChildren {
  client: ApiClient;
}

export function ApiClientProvider({ client, children }: ApiClientProviderProps) {
  return <ApiClientContext value={client}>{children}</ApiClientContext>;
}
