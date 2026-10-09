import { ServerOffIcon } from "lucide-react";
import type { ReactNode } from "react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { useApiClient } from "@/lib/api";
import { es } from "@/lib/i18n";

import { useBackendConnection } from "../hooks/useBackendConnection";

export interface ConnectionGateProps {
  children: ReactNode;
}

/**
 * Bloquea el contenido mientras el servidor central o sus dependencias no
 * estén disponibles (PRODUCT_DECISIONS §3: sin modo offline).
 */
export function ConnectionGate({ children }: ConnectionGateProps) {
  const api = useApiClient();
  const { state, isRetrying, retry } = useBackendConnection();

  if (state.status === "connected") return children;

  if (state.status === "checking") {
    return (
      <div role="status" className="flex items-center gap-2 text-sm text-muted-foreground">
        <Spinner aria-hidden="true" />
        {es.connection.checking}
      </div>
    );
  }

  const copy = es.connection.unavailable[state.component];
  return (
    <div className="flex-1 flex items-center justify-center p-8 bg-slate-100/70">
      <div className="max-w-xl w-full">
        <Alert variant="destructive" role="alert">
          <ServerOffIcon aria-hidden="true" />
          <AlertTitle>{copy.title}</AlertTitle>
          <AlertDescription className="flex flex-col items-start gap-3">
            <p>{copy.description}</p>
            <p>{es.connection.blockedNotice}</p>
            <p className="font-mono text-xs">
              {es.connection.serverAddress(api.baseUrl)} — {state.detail}
            </p>
            <Button variant="outline" onClick={retry} disabled={isRetrying}>
              {isRetrying && <Spinner data-icon="inline-start" aria-hidden="true" />}
              {isRetrying ? es.connection.retrying : es.connection.retry}
            </Button>
          </AlertDescription>
        </Alert>
      </div>
    </div>
  );
}
