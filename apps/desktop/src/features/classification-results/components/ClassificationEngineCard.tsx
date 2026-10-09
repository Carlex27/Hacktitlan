import { FlaskConical } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Empty, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from "@/components/ui/empty";
import { Skeleton } from "@/components/ui/skeleton";
import type { ClassificationResultDto, ClassificationRunDto } from "@/lib/api";
import { es } from "@/lib/i18n";
import { findSourceReferenceForCode, formatTariffCode, type TariffActionRenderer } from "../model";

export interface ClassificationEngineCardProps {
  run: ClassificationRunDto | null;
  result: ClassificationResultDto | null;
  isLoading?: boolean;
  onViewEvidence?: (evidenceId: number) => void;
  onSelectCandidateOpen?: () => void;
  renderTariffAction?: TariffActionRenderer;
}

export function ClassificationEngineCard({ run, result, isLoading = false, onSelectCandidateOpen, renderTariffAction }: ClassificationEngineCardProps) {
  if (isLoading) return <div role="status" aria-label={es.processingStatus.loading} className="space-y-4 rounded-xl border border-border bg-background p-5">
    <Skeleton className="h-6 w-48 max-w-full" /><Skeleton className="h-24 w-full" />
  </div>;
  if (!run || !result) return <Empty className="rounded-xl border border-border bg-background py-8">
    <EmptyHeader><EmptyMedia variant="icon"><FlaskConical aria-hidden="true" /></EmptyMedia>
      <EmptyTitle>{es.classification.noRunsTitle}</EmptyTitle><EmptyDescription>{es.classification.noRunsDescription}</EmptyDescription>
    </EmptyHeader>
  </Empty>;
  const topCandidate = result.candidates.find((candidate) => candidate.details.manual !== true) ?? null;
  const fraction = topCandidate?.fraction ?? result.fraction ?? null;
  const nico = topCandidate?.nico ?? result.nico ?? null;
  const code = formatTariffCode(fraction, nico);
  return <section aria-labelledby="class-engine-title" className="space-y-5 rounded-xl border border-border bg-background p-5 sm:p-6">
    <header className="flex flex-wrap items-center justify-between gap-3 border-b border-border pb-4">
      <h3 id="class-engine-title" className="text-lg leading-7 font-semibold">{es.classification.engineTitle}</h3>
      <div className="flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
        <span>{es.classification.runTitle(run.id)}</span>
        <Badge variant={run.approval_status === "rejected" ? "destructive" : "secondary"}>{es.workspace.status[run.approval_status]}</Badge>
      </div>
    </header>
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-3">
        <h4 className="text-sm leading-5 font-medium text-muted-foreground">{topCandidate ? es.classification.suggestedHeading : es.classification.manual.current}</h4>
        {topCandidate && <Badge variant="outline">{es.classification.supportLevel[topCandidate.support_level]}</Badge>}
      </div>
      <div className="flex flex-wrap items-center gap-4">
        <p className="text-2xl leading-8 font-semibold tabular-nums break-words">{code}</p>
        {renderTariffAction?.(findSourceReferenceForCode(result, fraction, nico), code)}
      </div>
      <p className="text-sm leading-6 text-muted-foreground">{topCandidate?.description ?? result.description ?? es.classification.noDescription}</p>
      {onSelectCandidateOpen && result.candidates.length > 0 && <Button variant="outline" className="min-h-11" onClick={onSelectCandidateOpen}>{es.classification.selectCandidateBtn} ({result.candidates.length})</Button>}
    </div>
  </section>;
}
