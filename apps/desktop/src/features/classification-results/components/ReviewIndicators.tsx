import { AlertCircle, CheckCircle2 } from "lucide-react";

import { Empty, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from "@/components/ui/empty";
import { es } from "@/lib/i18n";

import type { ReviewIndicator } from "../model";

export interface ReviewIndicatorsProps {
  indicators: readonly ReviewIndicator[];
}

export function ReviewIndicators({ indicators }: ReviewIndicatorsProps) {
  const outcomes: Readonly<Record<string, string>> = es.workspace.factorStatus;
  if (indicators.length === 0) {
    return (
      <Empty className="py-4">
        <EmptyHeader>
          <EmptyMedia variant="icon">
            <CheckCircle2 aria-hidden="true" className="w-5 h-5 text-success-foreground" />
          </EmptyMedia>
          <EmptyTitle className="text-sm">{es.classification.noRiskTitle}</EmptyTitle>
          <EmptyDescription className="text-sm">
            {es.classification.noRisks}
          </EmptyDescription>
        </EmptyHeader>
      </Empty>
    );
  }

  return (
    <div className="space-y-2">
      {indicators.map((ind, i) => (
        <div
          key={i}
          className="bg-warning-background border border-warning-border rounded-lg p-4 flex items-start gap-2 text-sm"
        >
          <AlertCircle aria-hidden="true" className="w-4 h-4 text-warning-foreground shrink-0 mt-0.5" />
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <span className="min-w-0 font-bold text-warning-foreground break-all">{ind.ruleCode}</span>
              <span className="shrink-0 text-sm font-medium px-1 rounded bg-warning-background text-warning-foreground">
                {outcomes[ind.outcome] ?? ind.outcome}
              </span>
            </div>
            <p className="text-sm text-warning-foreground mt-0.5 leading-snug">
              {ind.explanation}
            </p>
          </div>
        </div>
      ))}
    </div>
  );
}
