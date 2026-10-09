import { ExternalLink } from "lucide-react";

import { ProcessingStatusBadge } from "@/components/feedback";
import { Empty, EmptyDescription, EmptyHeader, EmptyTitle } from "@/components/ui/empty";
import type { DecisionStepDto } from "@/lib/api";
import { es } from "@/lib/i18n";

import { outcomeToProcessingStatus } from "../model";

export interface DecisionChecklistProps {
  steps: readonly DecisionStepDto[];
  onViewEvidence?: (evidenceId: number) => void;
}

export function DecisionChecklist({ steps, onViewEvidence }: DecisionChecklistProps) {
  if (steps.length === 0) {
    return (
      <Empty className="py-4">
        <EmptyHeader>
          <EmptyTitle className="text-xs">{es.classification.noSteps}</EmptyTitle>
          <EmptyDescription className="text-[11px]">
            No se han registrado pasos de evaluación.
          </EmptyDescription>
        </EmptyHeader>
      </Empty>
    );
  }

  return (
    <div className="space-y-2">
      {steps.map((step) => {
        const status = outcomeToProcessingStatus(step.outcome);

        return (
          <div
            key={step.id}
            className="bg-white border border-slate-200 rounded-lg p-2.5 text-xs space-y-1.5"
          >
            <div className="flex items-center justify-between gap-2">
              <span className="font-mono font-bold text-slate-800 text-[11px]">
                {step.rule_code}
              </span>
              <ProcessingStatusBadge status={status} />
            </div>

            {step.explanation && (
              <p className="text-[11px] text-slate-600 leading-relaxed">
                {step.explanation}
              </p>
            )}

            {step.evidence_links.length > 0 && (
              <div className="flex flex-wrap gap-1.5 pt-1 border-t border-slate-100">
                {step.evidence_links.map((link) => (
                  <button
                    key={link.id}
                    type="button"
                    onClick={() => onViewEvidence?.(link.id)}
                    className="inline-flex items-center gap-1 text-[10px] text-blue-600 hover:text-blue-800 bg-blue-50 px-1.5 py-0.5 rounded border border-blue-200 hover:border-blue-300"
                  >
                    <span>{es.classification.evidenceLink}</span>
                    <ExternalLink aria-hidden="true" className="w-2.5 h-2.5" />
                  </button>
                ))}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
