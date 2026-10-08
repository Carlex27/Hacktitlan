import { FlaskConical } from "lucide-react";

import { Empty, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from "@/components/ui/empty";
import { Skeleton } from "@/components/ui/skeleton";
import type { CertificateChemicalCompositionDto } from "@/lib/api";
import { es } from "@/lib/i18n";

import { formatChemicalCompositions } from "../model";

export interface ChemicalCompositionGridProps {
  compositions: readonly CertificateChemicalCompositionDto[];
  isLoading?: boolean;
}

export function ChemicalCompositionGrid({
  compositions,
  isLoading = false,
}: ChemicalCompositionGridProps) {
  if (isLoading) {
    return (
      <div className="bg-white p-3 rounded-lg border border-slate-200 shadow-sm space-y-2">
        <Skeleton className="h-4 w-48" />
        <div className="grid grid-cols-6 gap-2">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-10 w-full" />
          ))}
        </div>
      </div>
    );
  }

  const items = formatChemicalCompositions(compositions);

  if (items.length === 0) {
    return (
      <section
        className="bg-white p-3 rounded-lg border border-slate-200 shadow-sm"
        aria-labelledby="chem-comp-title"
      >
        <h4 id="chem-comp-title" className="font-bold text-slate-800 text-xs mb-2">
          {es.certificateReview.chemistry.title}
        </h4>
        <Empty className="py-3">
          <EmptyHeader>
            <EmptyMedia variant="icon">
              <FlaskConical aria-hidden="true" className="w-5 h-5 text-slate-400" />
            </EmptyMedia>
            <EmptyTitle className="text-xs">{es.certificateReview.chemistry.emptyTitle}</EmptyTitle>
            <EmptyDescription className="text-[11px]">
              {es.certificateReview.chemistry.emptyDescription}
            </EmptyDescription>
          </EmptyHeader>
        </Empty>
      </section>
    );
  }

  return (
    <section
      className="bg-white p-3 rounded-lg border border-slate-200 shadow-sm"
      aria-labelledby="chem-comp-title"
    >
      <div className="flex items-center justify-between mb-2.5">
        <h4 id="chem-comp-title" className="font-bold text-slate-800 text-xs">
          {es.certificateReview.chemistry.title}
        </h4>
        <span className="text-[10px] text-slate-500 font-medium">
          {items.length} {items.length === 1 ? "elemento" : "elementos"}
        </span>
      </div>

      <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 gap-1.5 text-center">
        {items.map((item) => (
          <div key={item.id} className="bg-slate-50/80 border border-slate-200 rounded p-1">
            <span className="text-[10px] font-bold text-slate-600 block mb-0.5">
              {item.element}
            </span>
            <span
              className="text-[11px] font-mono text-slate-900 block truncate"
              title={item.rawPercentage ?? item.percentageDisplay}
            >
              {item.percentageDisplay}
            </span>
          </div>
        ))}
      </div>
    </section>
  );
}
