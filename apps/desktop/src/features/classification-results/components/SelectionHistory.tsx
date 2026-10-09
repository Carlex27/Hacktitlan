import { History } from "lucide-react";

import { Empty, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from "@/components/ui/empty";
import type { ClassificationSelectionDto } from "@/lib/api";
import { es } from "@/lib/i18n";

export interface SelectionHistoryProps {
  selections: readonly ClassificationSelectionDto[];
}

export function SelectionHistory({ selections }: SelectionHistoryProps) {
  if (selections.length === 0) {
    return (
      <Empty className="py-4">
        <EmptyHeader>
          <EmptyMedia variant="icon">
            <History aria-hidden="true" className="w-5 h-5 text-muted-foreground" />
          </EmptyMedia>
          <EmptyTitle className="text-sm">{es.classification.noSelections}</EmptyTitle>
          <EmptyDescription className="text-sm">
            {es.classification.noSelectionDescription}
          </EmptyDescription>
        </EmptyHeader>
      </Empty>
    );
  }

  return (
    <div className="space-y-2">
      {selections.map((sel) => (
        <div
          key={sel.id}
          className="border-b border-border py-4 text-sm leading-6 space-y-3 last:border-0"
        >
          <div className="flex flex-wrap items-center justify-between gap-x-2 gap-y-0.5">
            <span className="min-w-0 font-semibold text-foreground">
              {sel.person_name}
            </span>
            <span className="text-sm text-muted-foreground">
              {new Date(sel.created_at).toLocaleString("es-MX")}
            </span>
          </div>

          <p className="text-sm text-foreground break-words">
            "{sel.reason}"
          </p>

          <div className="flex flex-wrap items-center justify-between gap-x-2 text-sm text-muted-foreground pt-0.5">
            <span>{es.classification.workstation}: {sel.workstation_name}</span>
            <span>{es.classification.candidateLabel(sel.candidate_id)}</span>
          </div>
        </div>
      ))}
    </div>
  );
}
