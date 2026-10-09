import { LoadErrorAlert } from "@/components/feedback";
import { RotateCwIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { Progress } from "@/components/ui/progress";
import { es } from "@/lib/i18n";
import { useReclassification } from "../hooks/useReclassification";
import type { ReactNode } from "react";

export function ReclassificationForm({ certificateId, onComplete, children }: { certificateId: number; onComplete(): void; children?: ReactNode }) {
  const state = useReclassification(certificateId, onComplete);
  return <section className="min-w-0 max-w-full space-y-3">
    <div className="flex flex-wrap items-center justify-end gap-3">
    <Button type="button" className="min-h-10" disabled={state.processing || state.submitting}
      onClick={() => void state.start(es.approval.defaultPerson, es.workspace.classifyReason)}>
      {state.submitting ? <Spinner aria-hidden="true" /> : <RotateCwIcon aria-hidden="true" />}
      {es.workspace.classify}
    </Button>
    {children}
    </div>
    {(state.submitting || state.processing) && <div className="space-y-2">
      <div role="status" className="flex flex-wrap justify-between gap-2 text-sm">
        <span>{state.submitting ? es.workspace.classifySubmitting : state.job?.status === "running" ? es.workspace.classifyRunning : es.workspace.classifyQueued}</span>
        {state.job && <span className="tabular-nums">{state.job.progress}%</span>}
      </div>
      <Progress value={state.job?.progress ?? null} aria-label={es.workspace.classifyProgress} className="h-2" />
      <p className="text-sm text-muted-foreground">{es.workspace.classifyPending}</p>
    </div>}
    {state.error !== null && <LoadErrorAlert title={es.classification.loadError} error={state.error}
      {...(state.jobId !== null ? { onRetry: state.retry } : {})} />}
    {state.job && state.job.status !== "queued" && state.job.status !== "running" &&
      <p role={state.job.status === "failed" ? "alert" : "status"}>{state.job.error_message ?? (state.job.status === "succeeded" ? es.workspace.classifyComplete : state.job.status === "needs_review" ? es.processingStatus.needs_review : state.job.status === "needs_ocr" ? es.certificateImport.item.needsOcr : state.job.status === "cancelled" ? es.certificateImport.item.cancelled : es.certificateImport.item.failed)}</p>}
  </section>;
}
