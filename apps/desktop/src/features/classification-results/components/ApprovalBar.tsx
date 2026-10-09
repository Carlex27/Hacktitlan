import { Check, X } from "lucide-react";
import { useId } from "react";

import { LoadErrorAlert } from "@/components/feedback";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { describeApiError, type CertificateDetailDto, type ClassificationRunDto } from "@/lib/api";
import { es } from "@/lib/i18n";

import { useRunApproval } from "../hooks/useRunApproval";
import { approvalCoverage } from "../model";
import { ApprovalOverview } from "./ApprovalOverview";

export interface ApprovalBarProps {
  run: ClassificationRunDto | null;
  certificate: CertificateDetailDto | null;
  isLoading?: boolean;
  loadError?: unknown;
  onDecisionComplete?: () => void;
}

export function ApprovalBar({ run, certificate, isLoading = false, loadError = null, onDecisionComplete }: ApprovalBarProps) {
  const { approveRun, rejectRun, isSubmitting, error, clearError } = useRunApproval();
  const personName = es.approval.defaultPerson;
  const reason = es.approval.defaultReason;
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

  const isApproved = run.approval_status === "approved";
  const isRejected = run.approval_status === "rejected";

  return (
    <footer className="bg-background rounded-xl border border-border p-5 sm:p-8 flex flex-col gap-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="space-y-2">
          <h3 className="text-xl leading-7 font-semibold">{es.approval.barTitle}</h3>
          <p className="text-sm leading-6 text-muted-foreground">{certificate?.id === run.certificate_id ? es.approval.appliesToHeats(certificate.heats.length) : es.approval.appliesToActa}</p>
        </div>
        <Badge className={`h-auto min-h-8 whitespace-normal gap-2 px-3 py-1 ${isApproved ? "bg-success-background text-success-foreground" : !isRejected && run.approval_status === "needs_review" ? "border-warning-border bg-warning-background text-warning-foreground" : ""}`} variant={isRejected ? "destructive" : "secondary"}>
          {isApproved && <Check aria-hidden="true" className="size-4" />}{es.workspace.status[run.approval_status]}
        </Badge>
      </div>
      <div id={coverageId} role="status" className="text-sm leading-6 text-foreground">
        <ApprovalOverview run={run} certificate={certificate} coverage={coverage} isLoading={isLoading} loadError={loadError} />
        {!isLoading && !loadError && coverage && !coverage.complete && !isApproved && <details className="mt-2">
          <summary className="min-h-11 cursor-pointer py-2 font-medium focus-visible:outline-2 focus-visible:outline-primary">{es.approval.pendingHeats}</summary>
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
      </div>
      {error && (
        <Alert variant="destructive" role="alert">
          <AlertTitle>{es.approval.errorTitle}</AlertTitle>
          <AlertDescription>{describeApiError(error)}</AlertDescription>
        </Alert>
      )}

      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <p className="max-w-prose text-sm leading-6 text-muted-foreground">{isApproved ? es.approval.confirmedActionsHint : es.approval.decisionHint}</p>
        <div className="flex flex-wrap items-center gap-2 self-end">

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
          {!isApproved && <Button
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
          </Button>}
        </div>
      </div>
    </footer>
  );
}
