import { useState } from "react";

import { LoadErrorAlert } from "@/components/feedback";
import type { ClassificationRunDto } from "@/lib/api";
import { es } from "@/lib/i18n";

import { extractReviewIndicators, findActiveResult } from "../model";
import { CandidateList } from "./CandidateList";
import { ClassificationEngineCard } from "./ClassificationEngineCard";
import { DecisionChecklist } from "./DecisionChecklist";
import { ResultSelector } from "./ResultSelector";
import { ReviewIndicators } from "./ReviewIndicators";

export interface ClassificationValidationTabProps {
  run: ClassificationRunDto | null;
  isLoading?: boolean;
  /** Falla al cargar la ejecución; tiene prioridad sobre el estado vacío. */
  error?: unknown;
  onViewEvidence: (linkId: number) => void;
  onReloadRun: () => void;
}

export function ClassificationValidationTab({
  run,
  isLoading,
  error = null,
  onViewEvidence,
  onReloadRun,
}: ClassificationValidationTabProps) {
  const [selectedResultId, setSelectedResultId] = useState<number | null>(null);

  if (error) {
    return (
      <LoadErrorAlert title={es.classification.loadError} error={error} onRetry={onReloadRun} />
    );
  }

  const results = run?.results ?? [];
  const activeResult = findActiveResult(results, selectedResultId);
  // La selección vigente la determina el backend (considera reemplazos).
  const currentSelection = activeResult?.current_selection ?? null;
  const reviewIndicators = extractReviewIndicators(activeResult);

  return (
    <>
      {results.length > 1 && (
        <ResultSelector
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
      />

      {activeResult && (
        <section
          aria-labelledby="candidates-heading"
          className="bg-white p-3.5 rounded-lg border border-slate-200 shadow-sm flex flex-col gap-2"
        >
          <h4 id="candidates-heading" className="font-bold text-slate-800 text-xs">
            {es.classification.candidatesTitle}
          </h4>
          {/* `key` reinicia el formulario al cambiar de producto. */}
          <CandidateList
            key={activeResult.id}
            resultId={activeResult.id}
            candidates={activeResult.candidates}
            selectedCandidateId={currentSelection?.candidate_id ?? null}
            onCandidateSelected={onReloadRun}
          />
        </section>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
        <section
          aria-labelledby="steps-heading"
          className="bg-white p-3 rounded-lg border border-slate-200 shadow-sm flex flex-col gap-2"
        >
          <h4 id="steps-heading" className="font-bold text-slate-800 text-xs">
            {es.classification.stepsTitle}
          </h4>
          <DecisionChecklist steps={activeResult?.steps ?? []} onViewEvidence={onViewEvidence} />
        </section>

        <section
          aria-labelledby="risks-heading"
          className="bg-white p-3 rounded-lg border border-slate-200 shadow-sm flex flex-col gap-2"
        >
          <h4 id="risks-heading" className="font-bold text-slate-800 text-xs">
            {es.classification.riskTitle}
          </h4>
          <ReviewIndicators indicators={reviewIndicators} />
        </section>
      </div>
    </>
  );
}
