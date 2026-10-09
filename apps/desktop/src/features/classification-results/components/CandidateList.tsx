import { Check } from "lucide-react";
import { useId, useState } from "react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Empty, EmptyDescription, EmptyHeader, EmptyTitle } from "@/components/ui/empty";
import { Spinner } from "@/components/ui/spinner";
import { describeApiError, type ClassificationCandidateDto } from "@/lib/api";
import { es } from "@/lib/i18n";
import { cn } from "@/lib/utils";

import { CandidateFactors } from "./CandidateFactors";
import { useCandidateSelection } from "../hooks/useCandidateSelection";
import { findCandidateSourceReference, formatTariffCode, type TariffActionRenderer } from "../model";

export interface CandidateListProps {
  resultId: number;
  disabled?: boolean;
  initialCandidateId?: number | null;
  onViewEvidence?: (id: number) => void;
  candidates: readonly ClassificationCandidateDto[];
  selectedCandidateId: number | null;
  onCandidateSelected?: (candidateId: number) => void;
  /** Acción opcional junto a cada código (p. ej. abrir su referencia en la LIGIE). */
  renderTariffAction?: TariffActionRenderer;
}

export function CandidateList({
  resultId,
  disabled = false,
  initialCandidateId,
  onViewEvidence,
  candidates,
  selectedCandidateId,
  onCandidateSelected,
  renderTariffAction,
}: CandidateListProps) {
  const { selectCandidate, deselect, isSubmitting, error, clearError } = useCandidateSelection();
  const [activeCandidateId, setActiveCandidateId] = useState<number | null>(
    initialCandidateId ?? selectedCandidateId ?? candidates[0]?.id ?? null,
  );
  const personId = useId();

  if (candidates.length === 0) {
    return (
      <Empty className="py-4">
        <EmptyHeader>
          <EmptyTitle className="text-sm">{es.classification.noCandidatesTitle}</EmptyTitle>
          <EmptyDescription className="text-sm">
            El clasificador no determinó candidatos para este resultado.
          </EmptyDescription>
        </EmptyHeader>
      </Empty>
    );
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    clearError();

    if (disabled || activeCandidateId === null) return;

    try {
      await selectCandidate(resultId, activeCandidateId, es.approval.defaultPerson, es.classification.defaultSelectionReason);
      onCandidateSelected?.(activeCandidateId);
    } catch {
      // Error handled by hook
    }
  }

  async function handleDeselect() {
    if (disabled || isSubmitting || selectedCandidateId === null) return;
    try {
      await deselect(resultId, es.approval.defaultPerson, es.classification.deselectionReason);
      setActiveCandidateId(null);
      onCandidateSelected?.(selectedCandidateId);
    } catch { /* El hook muestra el error. */ }
  }

  return (
    <div className="space-y-5">
      {error && (
        <Alert variant="destructive">
          <AlertTitle>{es.classification.selectionError}</AlertTitle>
          <AlertDescription>{describeApiError(error)}</AlertDescription>
        </Alert>
      )}

      <form onSubmit={handleSubmit} className="space-y-5">
        <div className="space-y-3" role="radiogroup" aria-label={es.classification.candidatesTitle}>
          {candidates.map((cand) => {
            const isChosen = activeCandidateId === cand.id;
            const code = formatTariffCode(cand.fraction, cand.nico);

            return (
              <label
                key={cand.id}
                className={cn(
                  "flex items-start gap-2.5 p-3 rounded-xl border cursor-pointer transition-colors",
                  isChosen
                    ? "bg-accent border-primary ring-1 ring-primary"
                    : "bg-background border-border hover:bg-muted/40",
                )}
              >
                <input
                  type="radio"
                  name={`candidate-${personId}`}
                  value={cand.id}
                  checked={isChosen}
                  disabled={disabled || isSubmitting}
                  onChange={() => setActiveCandidateId(cand.id)}
                  className="mt-1 size-4 shrink-0 accent-primary focus-visible:outline-2 focus-visible:outline-primary focus-visible:outline-offset-2"
                />
                <div className="flex-1 min-w-0">
                  <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
                    <span className="tabular-nums font-semibold text-foreground text-base leading-6 break-all">{code}</span>
                    <Badge variant={cand.support_level === "fully_supported" ? "default" : "outline"} className="text-sm">
                      {es.classification.supportLevel[cand.support_level] ?? cand.support_level}
                    </Badge>
                    <span className="text-sm text-muted-foreground font-mono">
                      {es.classification.rank(cand.rank)}
                    </span>
                    {renderTariffAction?.(findCandidateSourceReference(cand), code)}
                  </div>
                  {cand.description && (
                    <p className="text-sm text-muted-foreground mt-0.5 ">
                      {cand.description}
                    </p>
                  )}
                </div>
              </label>
            );
          })}
        </div>

        <CandidateFactors candidate={candidates.find((candidate) => candidate.id === activeCandidateId)}
          onViewEvidence={onViewEvidence} renderTariffAction={renderTariffAction} />
        <div className="border-t border-border pt-5 text-sm">
          <div className="pt-1 flex justify-end gap-2">
            {selectedCandidateId !== null && <Button type="button" variant="outline" className="min-h-10"
              disabled={disabled || isSubmitting} onClick={handleDeselect}>{es.classification.deselectCandidateBtn}</Button>}
            <Button
              type="submit"
              size="sm"
              disabled={disabled || isSubmitting || activeCandidateId === null}
              className="min-h-10"
            >
              {isSubmitting ? <Spinner className="w-3.5 h-3.5 mr-1" /> : <Check className="w-3.5 h-3.5 mr-1" />}
              {es.classification.selectCandidateBtn}
            </Button>
          </div>
        </div>
      </form>
    </div>
  );
}
