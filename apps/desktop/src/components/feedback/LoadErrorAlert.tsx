import { AlertTriangleIcon } from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { describeApiError } from "@/lib/api";
import { es } from "@/lib/i18n";

export interface LoadErrorAlertProps {
  title: string;
  error: unknown;
  onRetry?: () => void;
  /** Acción secundaria opcional, p. ej. cerrar un panel. */
  onDismiss?: () => void;
}

/** Falla de carga visible con opción de reintentar; nunca se oculta como "sin datos". */
export function LoadErrorAlert({ title, error, onRetry, onDismiss }: LoadErrorAlertProps) {
  return (
    <Alert variant="destructive" role="alert">
      <AlertTriangleIcon aria-hidden="true" />
      <AlertTitle>{title}</AlertTitle>
      <AlertDescription className="flex flex-col items-start gap-2">
        <p>{describeApiError(error)}</p>
        {(onRetry || onDismiss) && (
          <div className="flex gap-2">
            {onRetry && (
              <Button type="button" variant="outline" size="sm" onClick={onRetry}>
                {es.feedback.retry}
              </Button>
            )}
            {onDismiss && (
              <Button type="button" variant="ghost" size="sm" onClick={onDismiss}>
                {es.feedback.dismiss}
              </Button>
            )}
          </div>
        )}
      </AlertDescription>
    </Alert>
  );
}
