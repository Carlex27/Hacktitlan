import { AlertCircle, CheckCircle2 } from "lucide-react";

import { Empty, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from "@/components/ui/empty";
import { es } from "@/lib/i18n";

import type { ReviewIndicator } from "../model";

export interface ReviewIndicatorsProps {
  indicators: readonly ReviewIndicator[];
}

export function ReviewIndicators({ indicators }: ReviewIndicatorsProps) {
  if (indicators.length === 0) {
    return (
      <Empty className="py-4">
        <EmptyHeader>
          <EmptyMedia variant="icon">
            <CheckCircle2 aria-hidden="true" className="w-5 h-5 text-emerald-500" />
          </EmptyMedia>
          <EmptyTitle className="text-xs">Sin riesgos detectados</EmptyTitle>
          <EmptyDescription className="text-[11px]">
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
          className="bg-amber-50/80 border border-amber-200 rounded-lg p-2.5 flex items-start gap-2 text-xs"
        >
          <AlertCircle aria-hidden="true" className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
          <div className="min-w-0 flex-1">
            <div className="flex items-center justify-between gap-1">
              <span className="font-bold text-amber-900">{ind.ruleCode}</span>
              <span className="text-[10px] uppercase font-mono px-1 rounded bg-amber-200/60 text-amber-800">
                {ind.outcome}
              </span>
            </div>
            <p className="text-[11px] text-amber-800 mt-0.5 leading-snug">
              {ind.explanation}
            </p>
          </div>
        </div>
      ))}
    </div>
  );
}
