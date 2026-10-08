import { use } from "react";

import { ApiClientContext } from "./apiClientContext";
import type { ApiClient } from "./client";

export function useApiClient(): ApiClient {
  const client = use(ApiClientContext);
  if (!client) {
    throw new Error("useApiClient debe usarse dentro de ApiClientProvider");
  }
  return client;
}
