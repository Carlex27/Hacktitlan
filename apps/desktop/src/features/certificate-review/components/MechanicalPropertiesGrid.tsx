import { Wrench } from "lucide-react";

import { Empty, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from "@/components/ui/empty";
import { Skeleton } from "@/components/ui/skeleton";
import type { CertificateObservationDto } from "@/lib/api";
import { es } from "@/lib/i18n";

import { extractMechanicalProperties } from "../model";

export interface MechanicalPropertiesGridProps {
  observations: readonly CertificateObservationDto[];
  isLoading?: boolean;
}

export function MechanicalPropertiesGrid({
  observations,
  isLoading = false,
}: MechanicalPropertiesGridProps) {
  if (isLoading) {
    return (
      <div className="bg-white p-3 rounded-lg border border-slate-200 shadow-sm space-y-2">
        <Skeleton className="h-4 w-48" />
        <div className="grid grid-cols-2 gap-2">
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
        </div>
      </div>
    );
  }

  const items = extractMechanicalProperties(observations);

  if (items.length === 0) {
    return (
      <section
        className="bg-white p-3 rounded-lg border border-slate-200 shadow-sm"
        aria-labelledby="mech-prop-title"
      >
        <h4 id="mech-prop-title" className="font-bold text-slate-800 text-xs mb-2">
          {es.certificateReview.mechanics.title}
        </h4>
        <Empty className="py-3">
          <EmptyHeader>
            <EmptyMedia variant="icon">
              <Wrench aria-hidden="true" className="w-5 h-5 text-slate-400" />
            </EmptyMedia>
            <EmptyTitle className="text-xs">{es.certificateReview.mechanics.emptyTitle}</EmptyTitle>
            <EmptyDescription className="text-[11px]">
              {es.certificateReview.mechanics.emptyDescription}
            </EmptyDescription>
          </EmptyHeader>
        </Empty>
      </section>
    );
  }

  return (
    <section
      className="bg-white p-3 rounded-lg border border-slate-200 shadow-sm"
      aria-labelledby="mech-prop-title"
    >
      <div className="flex items-center justify-between mb-2.5">
        <h4 id="mech-prop-title" className="font-bold text-slate-800 text-xs">
          {es.certificateReview.mechanics.title}
        </h4>
        <span className="text-[10px] text-slate-500 font-medium">
          {items.length} {items.length === 1 ? "ensayo" : "ensayos"}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-2 text-left">
        {items.map((item) => (
          <div key={item.id} className="bg-slate-50/80 border border-slate-200 rounded p-1.5">
            <span className="text-[10px] text-slate-500 block mb-0.5 truncate" title={item.label}>
              {item.label}
            </span>
            <span className="text-[11px] font-medium text-slate-900 block truncate" title={item.value}>
              {item.value}
            </span>
          </div>
        ))}
      </div>
    </section>
  );
}
