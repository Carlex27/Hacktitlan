import { useId } from "react";
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
  const titleId = useId();
  if (isLoading) {
    return (
      <div className="bg-background p-5 rounded-xl border border-border space-y-2">
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
        className="bg-background p-5 rounded-xl border border-border"
        aria-labelledby={titleId}
      >
        <h4 id={titleId} className="font-semibold text-foreground text-lg leading-7 mb-2">
          {es.certificateReview.mechanics.title}
        </h4>
        <Empty className="py-3">
          <EmptyHeader>
            <EmptyMedia variant="icon">
              <Wrench aria-hidden="true" className="w-5 h-5 text-muted-foreground" />
            </EmptyMedia>
            <EmptyTitle className="text-sm">{es.certificateReview.mechanics.emptyTitle}</EmptyTitle>
            <EmptyDescription className="text-sm">
              {es.certificateReview.mechanics.emptyDescription}
            </EmptyDescription>
          </EmptyHeader>
        </Empty>
      </section>
    );
  }

  return (
    <section
      className="bg-background p-5 rounded-xl border border-border"
      aria-labelledby={titleId}
    >
      <div className="flex items-center justify-between mb-2.5">
        <h4 id={titleId} className="font-semibold text-foreground text-lg leading-7">
          {es.certificateReview.mechanics.title}
        </h4>
        <span className="text-sm text-muted-foreground font-medium">
          {es.certificateReview.mechanics.testCount(items.length)}
        </span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-left">
        {items.map((item) => (
          <div key={item.id} className="bg-muted/40 border border-border rounded-lg p-3">
            <span className="text-sm text-muted-foreground block mb-0.5 break-words" title={item.label}>
              {item.label}
            </span>
            <span className="text-sm font-medium text-foreground block break-words" title={item.value}>
              {item.value}
            </span>
          </div>
        ))}
      </div>
    </section>
  );
}
