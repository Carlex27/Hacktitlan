import { Check, X } from "lucide-react";
import { useId, useState } from "react";

import { LoadErrorAlert } from "@/components/feedback";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { describeApiError, type CertificateDetailDto, type ClassificationRunDto } from "@/lib/api";
import { es } from "@/lib/i18n";

import { useRunApproval } from "../hooks/useRunApproval";
import { approvalCoverage } from "../model";

export interface ApprovalBarProps {
  run: ClassificationRunDto | null;
  certificate: CertificateDetailDto | null;
  isLoading?: boolean;
  loadError?: unknown;
  onDecisionComplete?: () => void;
}

export function ApprovalBar({ run, certificate, isLoading = false, loadError = null, onDecisionComplete }: ApprovalBarProps) {
  const { approveRun, rejectRun, saveDraft, isSubmitting, error, clearError } = useRunApproval();
  const personName = es.approval.defaultPerson;
  const reason = es.approval.defaultReason;
  const [draftSaved, setDraftSaved] = useState(false);
  const coverageId = useId();

  if (!run) {
    if (loadError) return <LoadErrorAlert title={es.classification.loadError} error={loadError} />;
    return <p role="status">{isLoading ? es.approval.coverageLoading : es.classification.noRunsTitle}</p>;
  }
  const coverage = approvalCoverage(certificate, run);
  const canApprove = !isLoading && !loadError && coverage?.complete === true && run.approval_status !== "approved";

  async function handleApprove() {
    if (!run || !canApprove) return;
    clearError();
    try {
      await approveRun(run.id, personName.trim(), reason.trim());
      onDecisionComplete?.();
    } catch {
      // error is handled in hook
    }
  }

  async function handleReject() {
    if (!run) return;
    clearError();
    try {
      await rejectRun(run.id, personName.trim(), reason.trim());
      onDecisionComplete?.();
    } catch {
      // error is handled in hook
    }
  }

  async function handleDraft() {
    if (!run) return;
    clearError();
    setDraftSaved(false);
    try {
      await saveDraft(run.id, personName.trim(), reason.trim());
      setDraftSaved(true);
      onDecisionComplete?.();
    } catch { /* El hook muestra el error. */ }
  }

  const isApproved = run.approval_status === "approved";
  const isRejected = run.approval_status === "rejected";

  return (
    <footer className="bg-background rounded-xl border border-border p-4 sm:p-6 flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border pb-4">
        <h3 className="text-lg leading-7 font-semibold">{es.approval.barTitle}</h3>
        <div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
          {run.results.length > 1 && <span>{es.approval.appliesToAllProducts(run.results.length)}</span>}
          <span>{es.approval.statusBadge}</span>
          <Badge className={`h-auto min-h-7 whitespace-normal px-3 py-1 ${isApproved ? "bg-success-background text-success-foreground" : !isRejected && run.approval_status === "needs_review" ? "border-warning-border bg-warning-background text-warning-foreground" : ""}`} variant={isRejected ? "destructive" : "secondary"}>{es.workspace.status[run.approval_status]}</Badge>
        </div>
      </div>
      {!isApproved && <div id={coverageId} role="status" className="rounded-lg bg-muted/40 p-4 text-sm leading-6 text-foreground">
        {isLoading ? es.approval.coverageLoading : loadError || !coverage ? es.approval.coverageUnavailable
          : coverage.complete ? es.approval.coverageReady : es.approval.coveragePending}
        {!isLoading && !loadError && coverage && !coverage.complete && <details className="mt-2">
          <summary className="min-h-11 cursor-pointer py-2 font-medium focus-visible:outline-2 focus-visible:outline-primary">{es.approval.pendingProducts}</summary>
          <div className="max-h-64 overflow-y-auto break-words rounded-sm focus-visible:outline-2 focus-visible:outline-ring" tabIndex={0} aria-label={es.approval.pendingProducts}>
          {coverage.pendingHeats.length > 0 && <p>{es.approval.pendingHeats}: {coverage.pendingHeats.map((heat) => heat.heat_no ?? `#${heat.id}`).join(", ")}</p>}
          {coverage.pendingProducts.length > 0 && <p>{es.approval.pendingProducts}: {coverage.pendingProducts.map((product) => product.product_identifier ?? `#${product.id}`).join(", ")}</p>}
          {coverage.pendingConditions.map(({ product, hasConflicts, factors }) => <div key={product.id} className="mt-3">
            <p className="font-medium">{product.product_identifier ?? `#${product.id}`}</p>
            {hasConflicts && <p>{es.approval.conflictingData}</p>}
            {factors.map((factor) => <p key={factor.id}>{factor.explanation || factor.rule_code} · {es.workspace.factorStatus[factor.outcome]}</p>)}
          </div>)}
          </div>
        </details>}
      </div>}
      {draftSaved && <p role="status" className="text-sm text-success-foreground">{es.workspace.draftSaved}</p>}
      {error && (
        <Alert variant="destructive" role="alert">
          <AlertTitle>{es.approval.errorTitle}</AlertTitle>
          <AlertDescription>{describeApiError(error)}</AlertDescription>
        </Alert>
      )}

      <div className="flex flex-wrap items-center justify-end gap-3 border-t border-border pt-4">
        {/* Status Badge & Actions */}
        <div className="flex flex-wrap items-center gap-2 self-end">

          <Button className="min-h-11" type="button" variant="outline" onClick={handleDraft} disabled={isSubmitting || isApproved}>{es.workspace.draft}</Button>
          {/* Reject Button */}
          <Button
            type="button"
            variant="destructive"
            size="sm"
            onClick={handleReject}
            disabled={isSubmitting}
            className="min-h-11 text-sm"
          >
            {isSubmitting ? (
              <Spinner className="w-3.5 h-3.5 mr-1" />
            ) : (
              <X aria-hidden="true" className="w-3.5 h-3.5 mr-1" />
            )}
            <span>{es.approval.rejectBtn}</span>
          </Button>

          {/* Approve Button */}
          <Button
            type="button"
            size="sm"
            onClick={handleApprove}
            disabled={isSubmitting || !canApprove}
            aria-describedby={!isApproved ? coverageId : undefined}
            className="min-h-11 text-sm"
          >
            {isSubmitting ? (
              <Spinner className="w-3.5 h-3.5 mr-1" />
            ) : (
              <Check aria-hidden="true" className="w-3.5 h-3.5 mr-1 stroke-[2.5]" />
            )}
            <span>{es.approval.approveBtn}</span>
          </Button>
        </div>
      </div>
    </footer>
  );
}
