import { LoadErrorAlert } from "@/components/feedback";
import { Spinner } from "@/components/ui/spinner";
import { es } from "@/lib/i18n";

import type { EvidenceState } from "../hooks/useEvidence";
import { EvidencePanel } from "./EvidencePanel";

export interface EvidenceAreaProps {
  state: EvidenceState;
  onRetry(): void;
  onClose(): void;
  onGoToPage?: (page: number) => void;
}

/** Muestra la evidencia solicitada con sus estados de carga y error. */
export function EvidenceArea({ state, onRetry, onClose, onGoToPage }: EvidenceAreaProps) {
  switch (state.status) {
    case "idle":
      return null;
    case "loading":
      return (
        <div role="status" className="flex items-center gap-2 text-xs text-slate-500">
          <Spinner aria-hidden="true" />
          {es.evidence.loading}
        </div>
      );
    case "error":
      return (
        <LoadErrorAlert
          title={es.evidence.loadError}
          error={state.error}
          onRetry={onRetry}
          onDismiss={onClose}
        />
      );
    case "success":
      return (
        <EvidencePanel
          evidence={state.evidence}
          onClose={onClose}
          {...(onGoToPage ? { onGoToPage } : {})}
        />
      );
  }
}
