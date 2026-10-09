import { ProcessingStatusBadge } from "@/components/feedback";
import { Empty, EmptyDescription, EmptyHeader, EmptyTitle } from "@/components/ui/empty";
import type { DecisionStepDto } from "@/lib/api";
import { es } from "@/lib/i18n";

import { outcomeToProcessingStatus } from "../model";
import { FactorEvidenceButton } from "./FactorEvidenceButton";

export interface DecisionChecklistProps {
  steps: readonly DecisionStepDto[];
  onViewEvidence?: (evidenceId: number) => void;
}

export function DecisionChecklist({ steps, onViewEvidence }: DecisionChecklistProps) {
  if (steps.length === 0) {
    return (
      <Empty className="py-4">
        <EmptyHeader>
          <EmptyTitle className="text-sm">{es.classification.noSteps}</EmptyTitle>
          <EmptyDescription className="text-sm">
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
            className="border-b border-border py-4 text-sm space-y-3 last:border-0"
          >
            <div className="flex flex-wrap items-start justify-between gap-2">
              <span className="min-w-0 font-medium text-foreground text-sm leading-6 break-words">
                {step.rule_code}
              </span>
              <span className="shrink-0">
                <ProcessingStatusBadge status={status} />
              </span>
            </div>

            {step.explanation && (
              <p className="text-sm text-muted-foreground leading-relaxed">
                {step.explanation}
              </p>
            )}

            {step.evidence_links.length > 0 && onViewEvidence && (
              <div className="flex flex-wrap gap-1.5 pt-1 border-t border-border">
                <FactorEvidenceButton links={step.evidence_links} onOpen={onViewEvidence} />
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
