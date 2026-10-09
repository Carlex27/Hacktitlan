import { Check } from "lucide-react";
import { useId, useState } from "react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Empty, EmptyDescription, EmptyHeader, EmptyTitle } from "@/components/ui/empty";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { Textarea } from "@/components/ui/textarea";
import { describeApiError, type ClassificationCandidateDto } from "@/lib/api";
import { es } from "@/lib/i18n";
import { cn } from "@/lib/utils";

import { useCandidateSelection } from "../hooks/useCandidateSelection";
import { formatTariffCode, type TariffActionRenderer } from "../model";

export interface CandidateListProps {
  resultId: number;
  candidates: readonly ClassificationCandidateDto[];
  selectedCandidateId: number | null;
  onCandidateSelected?: (candidateId: number) => void;
  /** Acción opcional junto a cada código (p. ej. abrir su referencia en la LIGIE). */
  renderTariffAction?: TariffActionRenderer;
}

export function CandidateList({
  resultId,
  candidates,
  selectedCandidateId,
  onCandidateSelected,
  renderTariffAction,
}: CandidateListProps) {
  const { selectCandidate, isSubmitting, error, clearError } = useCandidateSelection();
  const [activeCandidateId, setActiveCandidateId] = useState<number | null>(
    selectedCandidateId ?? candidates[0]?.id ?? null,
  );
  const [personName, setPersonName] = useState("");
  const [reason, setReason] = useState("");
  const [validationErrors, setValidationErrors] = useState<{ person?: string; reason?: string }>({});

  const personId = useId();
  const reasonId = useId();
  const personErrId = useId();
  const reasonErrId = useId();

  if (candidates.length === 0) {
    return (
      <Empty className="py-4">
        <EmptyHeader>
          <EmptyTitle className="text-xs">Sin candidatos disponibles</EmptyTitle>
          <EmptyDescription className="text-[11px]">
            El clasificador no determinó candidatos para este resultado.
          </EmptyDescription>
        </EmptyHeader>
      </Empty>
    );
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    clearError();

    const errors: { person?: string; reason?: string } = {};
    if (personName.trim().length < 2) {
      errors.person = es.approval.personRequired;
    }
    if (reason.trim().length < 3) {
      errors.reason = es.approval.reasonRequired;
    }

    if (Object.keys(errors).length > 0) {
      setValidationErrors(errors);
      return;
    }

    setValidationErrors({});

    if (activeCandidateId === null) return;

    try {
      await selectCandidate(resultId, activeCandidateId, personName.trim(), reason.trim());
      onCandidateSelected?.(activeCandidateId);
    } catch {
      // Error handled by hook
    }
  }

  return (
    <div className="space-y-3">
      {error && (
        <Alert variant="destructive">
          <AlertTitle>Error al seleccionar candidato</AlertTitle>
          <AlertDescription>{describeApiError(error)}</AlertDescription>
        </Alert>
      )}

      <form onSubmit={handleSubmit} className="space-y-3">
        <div className="space-y-1.5" role="radiogroup" aria-label={es.classification.candidatesTitle}>
          {candidates.map((cand) => {
            const isChosen = activeCandidateId === cand.id;
            const code = formatTariffCode(cand.fraction, cand.nico);

            return (
              <label
                key={cand.id}
                className={cn(
                  "flex items-start gap-2.5 p-2 rounded-lg border cursor-pointer transition-all",
                  isChosen
                    ? "bg-blue-50/70 border-blue-400 ring-1 ring-blue-400"
                    : "bg-white border-slate-200 hover:bg-slate-50",
                )}
              >
                <input
                  type="radio"
                  name="candidate"
                  value={cand.id}
                  checked={isChosen}
                  onChange={() => setActiveCandidateId(cand.id)}
                  className="mt-0.5 text-blue-600 focus:ring-blue-500"
                />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-mono font-bold text-slate-900 text-xs">{code}</span>
                    <Badge variant={cand.support_level === "fully_supported" ? "default" : "outline"} className="text-[9.5px]">
                      {es.classification.supportLevel[cand.support_level] ?? cand.support_level}
                    </Badge>
                    <span className="text-[10px] text-slate-400 font-mono">
                      {es.classification.rank(cand.rank)}
                    </span>
                    {renderTariffAction?.(cand.fraction, cand.nico, code)}
                  </div>
                  {cand.description && (
                    <p className="text-[10.5px] text-slate-600 mt-0.5 line-clamp-2">
                      {cand.description}
                    </p>
                  )}
                </div>
              </label>
            );
          })}
        </div>

        {/* Input de Persona y Motivo para auditoría */}
        <div className="bg-slate-50 border border-slate-200 rounded-lg p-2.5 space-y-2 text-xs">
          <div>
            <label htmlFor={personId} className="block text-[11px] font-semibold text-slate-700 mb-0.5">
              {es.approval.personLabel} <span className="text-red-500">*</span>
            </label>
            <Input
              id={personId}
              value={personName}
              onChange={(e) => {
                setPersonName(e.target.value);
                if (validationErrors.person) {
                  setValidationErrors((v) => {
                    const next = { ...v };
                    delete next.person;
                    return next;
                  });
                }
              }}
              placeholder={es.approval.personPlaceholder}
              disabled={isSubmitting}
              aria-invalid={Boolean(validationErrors.person)}
              aria-describedby={validationErrors.person ? personErrId : undefined}
              className="h-8 text-xs bg-white"
            />
            {validationErrors.person && (
              <p id={personErrId} role="alert" className="text-[10.5px] text-red-600 mt-0.5">
                {validationErrors.person}
              </p>
            )}
          </div>

          <div>
            <label htmlFor={reasonId} className="block text-[11px] font-semibold text-slate-700 mb-0.5">
              {es.approval.reasonLabel} <span className="text-red-500">*</span>
            </label>
            <Textarea
              id={reasonId}
              value={reason}
              onChange={(e) => {
                setReason(e.target.value);
                if (validationErrors.reason) {
                  setValidationErrors((v) => {
                    const next = { ...v };
                    delete next.reason;
                    return next;
                  });
                }
              }}
              placeholder={es.approval.reasonPlaceholder}
              disabled={isSubmitting}
              aria-invalid={Boolean(validationErrors.reason)}
              aria-describedby={validationErrors.reason ? reasonErrId : undefined}
              rows={2}
              className="text-xs bg-white"
            />
            {validationErrors.reason && (
              <p id={reasonErrId} role="alert" className="text-[10.5px] text-red-600 mt-0.5">
                {validationErrors.reason}
              </p>
            )}
          </div>

          <div className="pt-1 flex justify-end">
            <Button
              type="submit"
              size="sm"
              disabled={isSubmitting || activeCandidateId === null}
              className="bg-blue-600 hover:bg-blue-700 text-white"
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
