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
      <div className="border-b border-border pb-6 space-y-2">
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
        className="border-b border-border pb-6"
        aria-labelledby="chem-comp-title"
      >
        <h4 id="chem-comp-title" className="font-semibold text-foreground text-lg leading-7 mb-2">
          {es.certificateReview.chemistry.title}
        </h4>
        <Empty className="py-3">
          <EmptyHeader>
            <EmptyMedia variant="icon">
              <FlaskConical aria-hidden="true" className="w-5 h-5 text-muted-foreground" />
            </EmptyMedia>
            <EmptyTitle className="text-sm">{es.certificateReview.chemistry.emptyTitle}</EmptyTitle>
            <EmptyDescription className="text-sm">
              {es.certificateReview.chemistry.emptyDescription}
            </EmptyDescription>
          </EmptyHeader>
        </Empty>
      </section>
    );
  }

  return (
    <section
      className="border-b border-border pb-6"
      aria-labelledby="chem-comp-title"
    >
      <div className="flex flex-wrap items-center justify-between gap-2 mb-4">
        <h4 id="chem-comp-title" className="font-semibold text-foreground text-lg leading-7">
          {es.certificateReview.chemistry.title}
        </h4>
        <span className="text-sm text-muted-foreground font-medium">
          {es.certificateReview.chemistry.elementCount(items.length)}
        </span>
      </div>

      <div className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,7.5rem),1fr))] gap-2 text-center">
        {items.map((item) => (
          <div key={item.id} className="bg-background rounded-lg px-3 py-4">
            <span className="text-sm font-semibold text-muted-foreground block mb-0.5">
              {item.element}
            </span>
            <span
              className="text-base font-medium tabular-nums text-foreground block break-words"
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
