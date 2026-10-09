import {
  ApiError,
  describeApiError,
  getHealthLive,
  getHealthReady,
  type ApiClient,
} from "@/lib/api";

/** Componente que impide operar: el servidor completo o sus dependencias. */
export type UnavailableComponent = "server" | "dependencies";

export type ConnectionState =
  | { status: "checking" }
  | { status: "connected" }
  | { status: "unavailable"; component: UnavailableComponent; detail: string };

/**
 * Distingue entre servidor inalcanzable (backend apagado o Tailscale caído) y
 * servidor activo con PostgreSQL o almacenamiento no disponibles.
 */
export async function checkConnection(
  api: ApiClient,
  signal?: AbortSignal,
): Promise<ConnectionState> {
  try {
    await getHealthLive(api, { signal });
  } catch (error) {
    if (error instanceof ApiError && error.kind === "aborted") throw error;
    return { status: "unavailable", component: "server", detail: describeApiError(error) };
  }

  try {
    await getHealthReady(api, { signal });
  } catch (error) {
    if (error instanceof ApiError && error.kind === "aborted") throw error;
    const component: UnavailableComponent =
      error instanceof ApiError && error.kind === "network" ? "server" : "dependencies";
    return { status: "unavailable", component, detail: describeApiError(error) };
  }

  return { status: "connected" };
}
