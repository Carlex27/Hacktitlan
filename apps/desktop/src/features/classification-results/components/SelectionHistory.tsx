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
            <History aria-hidden="true" className="w-5 h-5 text-slate-400" />
          </EmptyMedia>
          <EmptyTitle className="text-xs">{es.classification.noSelections}</EmptyTitle>
          <EmptyDescription className="text-[11px]">
            No hay auditoría de selección previa en esta corrida.
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
          className="bg-white border border-slate-200 rounded-lg p-2.5 text-xs space-y-1"
        >
          <div className="flex items-center justify-between gap-2">
            <span className="font-semibold text-slate-800">
              {sel.person_name}
            </span>
            <span className="text-[10.5px] text-slate-400">
              {new Date(sel.created_at).toLocaleString("es-MX")}
            </span>
          </div>

          <p className="text-[11px] text-slate-700 italic bg-slate-50 p-1.5 rounded border border-slate-100">
            "{sel.reason}"
          </p>

          <div className="flex items-center justify-between text-[10px] text-slate-500 pt-0.5">
            <span>{es.classification.workstation}: {sel.workstation_name}</span>
            <span>Candidato #{sel.candidate_id}</span>
          </div>
        </div>
      ))}
    </div>
  );
}
