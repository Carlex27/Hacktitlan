import { Check, CheckCircle2, ChevronRight, FlaskConical, HelpCircle, XCircle } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Empty, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from "@/components/ui/empty";
import { Skeleton } from "@/components/ui/skeleton";
import type { ClassificationResultDto, ClassificationRunDto } from "@/lib/api";
import { es } from "@/lib/i18n";
import { cn } from "@/lib/utils";

import {
  extractReviewIndicators,
  findSourceReferenceForCode,
  formatTariffCode,
  type TariffActionRenderer,
} from "../model";

export interface ClassificationEngineCardProps {
  run: ClassificationRunDto | null;
  result: ClassificationResultDto | null;
  isLoading?: boolean;
  onViewEvidence?: (evidenceId: number) => void;
  onSelectCandidateOpen?: () => void;
  /** Acción opcional junto a cada código (p. ej. abrir su referencia en la LIGIE). */
  renderTariffAction?: TariffActionRenderer;
}

export function ClassificationEngineCard({
  run,
  result,
  isLoading = false,
  onViewEvidence,
  onSelectCandidateOpen,
  renderTariffAction,
}: ClassificationEngineCardProps) {
  if (isLoading) {
    return (
      <div className="bg-white p-3.5 rounded-lg border border-slate-200 shadow-sm space-y-3">
        <Skeleton className="h-5 w-48" />
        <div className="grid grid-cols-12 gap-4">
          <Skeleton className="col-span-4 h-32" />
          <Skeleton className="col-span-4 h-32" />
          <Skeleton className="col-span-4 h-32" />
        </div>
      </div>
    );
  }

  if (!run || !result) {
    return (
      <section
        className="bg-white p-4 rounded-lg border border-slate-200 shadow-sm"
        aria-labelledby="class-engine-empty"
      >
        <Empty className="py-4">
          <EmptyHeader>
            <EmptyMedia variant="icon">
              <FlaskConical aria-hidden="true" className="w-6 h-6 text-slate-400" />
            </EmptyMedia>
            <EmptyTitle id="class-engine-empty">
              {es.classification.noRunsTitle}
            </EmptyTitle>
            <EmptyDescription>
              {es.classification.noRunsDescription}
            </EmptyDescription>
          </EmptyHeader>
        </Empty>
      </section>
    );
  }

  const topCandidate = result.candidates[0] ?? null;
  const shownFraction = result.fraction ?? topCandidate?.fraction ?? null;
  const shownNico = result.nico ?? topCandidate?.nico ?? null;
  const tariffCode = formatTariffCode(shownFraction, shownNico);
  const isDetermined = tariffCode !== es.classification.noCandidate;
  const reviewIndicators = extractReviewIndicators(result);
  const steps = result.steps ?? [];

  return (
    <section
      className="bg-white p-3.5 rounded-lg border border-slate-200 shadow-sm"
      aria-labelledby="class-engine-title"
    >
      {/* Header with Run Title & Status */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-2.5 mb-3">
        <div className="flex min-w-0 flex-wrap items-center gap-2">
          <div className="w-6 h-6 rounded bg-indigo-50 border border-indigo-200 flex items-center justify-center text-indigo-600">
            <FlaskConical aria-hidden="true" className="w-3.5 h-3.5" />
          </div>
          <h4 id="class-engine-title" className="font-bold text-slate-900 text-xs">
            {es.classification.engineTitle}
          </h4>
          <span className="text-[11px] text-slate-500 font-medium">
            {es.classification.runTitle(run.id)}
          </span>
          <Badge
            variant={
              run.approval_status === "approved"
                ? "default"
                : run.approval_status === "rejected"
                  ? "destructive"
                  : "outline"
            }
          >
            {run.approval_status}
          </Badge>
        </div>

        {onSelectCandidateOpen && result.candidates.length > 0 && (
          <button
            type="button"
            onClick={onSelectCandidateOpen}
            className="text-xs text-blue-600 hover:text-blue-800 font-medium flex items-center gap-1"
          >
            {es.classification.selectCandidateBtn} ({result.candidates.length})
            <ChevronRight aria-hidden="true" className="w-3.5 h-3.5" />
          </button>
        )}
      </div>

      {/* Content Columns: Suggested / Match Details / Risk Indicators */}
      <div className="grid grid-cols-1 md:grid-cols-12 gap-4">
        {/* Suggested Classification */}
        <div
          className={cn(
            "col-span-12 md:col-span-4 rounded-lg p-3 flex flex-col justify-between border",
            isDetermined
              ? "bg-emerald-50/50 border-emerald-200"
              : "bg-slate-50 border-slate-200",
          )}
        >
          <div>
            <div className="flex items-center justify-between mb-1">
              <span className="text-[10.5px] font-semibold text-slate-500 block">
                {es.classification.suggestedHeading}
              </span>
              {topCandidate && (
                <Badge variant={topCandidate.support_level === "fully_supported" ? "default" : "outline"} className="text-[9.5px]">
                  {es.classification.supportLevel[topCandidate.support_level] ?? topCandidate.support_level}
                </Badge>
              )}
            </div>

            <div className="flex flex-wrap items-center justify-between gap-1 my-1">
              <span className="min-w-0 text-lg font-black text-slate-900 tracking-tight font-mono break-all">
                {tariffCode}
              </span>
              {renderTariffAction?.(findSourceReferenceForCode(result, shownFraction, shownNico), tariffCode)}
              {isDetermined && (
                <span className="w-5 h-5 rounded-full bg-emerald-500 text-white flex items-center justify-center shrink-0">
                  <Check aria-hidden="true" className="w-3.5 h-3.5 stroke-[3]" />
                </span>
              )}
            </div>

            <p className="text-[10px] text-slate-600 mt-2 leading-relaxed">
              {result.description ?? topCandidate?.description ?? "Sin descripción arancelaria"}
            </p>
          </div>
        </div>

        {/* Match Details Checklist */}
        <div className="col-span-12 md:col-span-4 space-y-1.5 text-[11px] border-l md:border-l border-slate-100 pl-3">
          <span className="text-[11px] font-bold text-slate-800 block mb-1">
            {es.classification.stepsTitle}
          </span>
          {steps.length === 0 ? (
            <p className="text-[10.5px] text-slate-400 italic">{es.classification.noSteps}</p>
          ) : (
            <div className="space-y-1.5 max-h-44 overflow-y-auto pr-1">
              {steps.map((step) => {
                const isMatched = step.outcome === "matched";
                const isNotMatched = step.outcome === "not_matched";
                const firstEvidence = step.evidence_links[0];

                return (
                  <div key={step.id} className="flex items-start gap-1.5 text-slate-700">
                    {isMatched ? (
                      <CheckCircle2 aria-hidden="true" className="w-3.5 h-3.5 text-emerald-500 shrink-0 mt-0.5" />
                    ) : isNotMatched ? (
                      <XCircle aria-hidden="true" className="w-3.5 h-3.5 text-red-500 shrink-0 mt-0.5" />
                    ) : (
                      <HelpCircle aria-hidden="true" className="w-3.5 h-3.5 text-amber-500 shrink-0 mt-0.5" />
                    )}

                    <div className="min-w-0 flex-1">
                      <div className="flex items-center justify-between gap-1">
                        <span className="font-semibold text-slate-800 truncate" title={step.rule_code}>
                          {step.rule_code}
                        </span>
                        {firstEvidence && onViewEvidence && (
                          <button
                            type="button"
                            onClick={() => onViewEvidence(firstEvidence.id)}
                            className="text-[10px] text-blue-600 hover:underline shrink-0"
                          >
                            {es.classification.evidenceLink}
                          </button>
                        )}
                      </div>
                      {step.explanation && (
                        <p className="text-[10px] text-slate-500 leading-snug line-clamp-2" title={step.explanation}>
                          {step.explanation}
                        </p>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Risk / Review Indicators */}
        <div className="col-span-12 md:col-span-4 pl-3 border-l border-slate-100 space-y-1.5 text-[11px]">
          <span className="text-[11px] font-bold text-slate-800 block mb-1">
            {es.classification.riskTitle}
          </span>
          {reviewIndicators.length === 0 ? (
            <p className="text-[10.5px] text-slate-400 italic">
              {es.classification.noRisks}
            </p>
          ) : (
            <div className="space-y-1.5 max-h-44 overflow-y-auto pr-1">
              {reviewIndicators.map((ind, i) => (
                <div key={i} className="flex items-start gap-1.5 text-amber-800 bg-amber-50/70 border border-amber-200/60 rounded p-1.5">
                  <HelpCircle aria-hidden="true" className="w-3.5 h-3.5 text-amber-600 shrink-0 mt-0.5" />
                  <div className="min-w-0 flex-1">
                    <span className="font-bold text-[10.5px] block truncate">{ind.ruleCode}</span>
                    <span className="text-[10px] text-amber-700 block">{ind.explanation}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
