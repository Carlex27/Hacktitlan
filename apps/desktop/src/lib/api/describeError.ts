import { es } from "@/lib/i18n";

import { ApiError } from "./errors";

/** Mensaje legible para el usuario a partir de cualquier error del cliente. */
export function describeApiError(error: unknown): string {
  if (error instanceof ApiError) {
    switch (error.kind) {
      case "server":
        return error.message;
      case "network":
        return es.errors.network;
      case "invalid_response":
        return es.errors.invalidResponse;
      case "aborted":
        return error.message;
    }
  }
  return es.errors.unexpected;
}
