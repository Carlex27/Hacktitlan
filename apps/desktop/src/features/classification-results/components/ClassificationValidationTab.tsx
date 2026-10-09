import { useState } from "react";

import { LoadErrorAlert } from "@/components/feedback";
import type { CertificateProductDto, ClassificationRunDto } from "@/lib/api";
import { es } from "@/lib/i18n";

import { findActiveResult, type TariffActionRenderer } from "../model";
import { CandidateList } from "./CandidateList";
import { ClassificationEngineCard } from "./ClassificationEngineCard";
import { ResultSelector } from "./ResultSelector";
import { ManualClassificationForm } from "./ManualClassificationForm";

export interface ClassificationValidationTabProps {
  run: ClassificationRunDto | null;
  products?: readonly CertificateProductDto[];
  resultId?: number;
  initialCandidateId?: number | null;
  isLoading?: boolean;
  /** Falla al cargar la ejecución; tiene prioridad sobre el estado vacío. */
  error?: unknown;
  onViewEvidence: (linkId: number) => void;
  onReloadRun: () => void;
  /** Acción opcional junto a cada código (p. ej. abrir su referencia en la LIGIE). */
  renderTariffAction?: TariffActionRenderer;
}

export function ClassificationValidationTab({
  run,
  products = [],
  resultId,
  initialCandidateId,
  isLoading,
  error = null,
  onViewEvidence,
  onReloadRun,
  renderTariffAction,
}: ClassificationValidationTabProps) {
  const [selectedResultId, setSelectedResultId] = useState<number | null>(null);

  if (error) {
    return (
      <LoadErrorAlert title={es.classification.loadError} error={error} onRetry={onReloadRun} />
    );
  }

  const results = run?.results ?? [];
  const activeResult = findActiveResult(results, resultId ?? selectedResultId);
  // La selección vigente la determina el backend (considera reemplazos).
  const currentSelection = activeResult?.current_selection ?? null;

  return (
    <>
      {resultId === undefined && results.length > 1 && (
        <ResultSelector
          products={products}
          results={results}
          activeResultId={activeResult?.id ?? null}
          onSelect={setSelectedResultId}
        />
      )}

      <ClassificationEngineCard
        run={run}
        result={activeResult}
        isLoading={Boolean(isLoading)}
        onViewEvidence={onViewEvidence}
        {...(renderTariffAction ? { renderTariffAction } : {})}
      />

      {!isLoading && activeResult && (
        <section
          aria-labelledby="candidates-heading"
          className="bg-background p-5 rounded-xl border border-border flex flex-col gap-2"
        >
          <h4 id="candidates-heading" className="font-semibold text-foreground text-lg leading-7">
            {es.classification.candidatesTitle}
          </h4>
          {/* `key` reinicia el formulario al cambiar de producto. */}
          <CandidateList
            key={`${activeResult.id}:${currentSelection?.id ?? "none"}:${initialCandidateId ?? "current"}`}
            onViewEvidence={onViewEvidence}
            resultId={activeResult.id}
            disabled={run?.approval_status === "approved"}
            initialCandidateId={initialCandidateId ?? null}
            candidates={activeResult.candidates.filter((candidate) => candidate.details.manual !== true)}
            selectedCandidateId={currentSelection?.candidate_id ?? null}
            onCandidateSelected={onReloadRun}
            {...(renderTariffAction ? { renderTariffAction } : {})}
          />
        </section>
      )}

      {!isLoading && activeResult && <ManualClassificationForm key={activeResult.id} result={activeResult}
        disabled={run?.approval_status === "approved"} onSaved={onReloadRun} />}
    </>
  );
}
