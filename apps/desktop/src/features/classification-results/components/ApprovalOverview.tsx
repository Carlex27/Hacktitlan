import { CheckCircle2, CircleAlert, CircleX } from "lucide-react";
import type { CertificateDetailDto, ClassificationRunDto } from "@/lib/api";
import { es } from "@/lib/i18n";
import { cn } from "@/lib/utils";
import type { approvalCoverage } from "../model";

interface ApprovalOverviewProps {
  run: ClassificationRunDto;
  certificate: CertificateDetailDto | null;
  coverage: ReturnType<typeof approvalCoverage>;
  isLoading: boolean;
  loadError: unknown;
}

export function ApprovalOverview({ run, certificate, coverage, isLoading, loadError }: ApprovalOverviewProps) {
  const approved = run.approval_status === "approved";
  const rejected = run.approval_status === "rejected";
  const available = !isLoading && !loadError && coverage && certificate;
  const ready = available && coverage.complete;
  const Icon = approved || ready ? CheckCircle2 : rejected ? CircleX : CircleAlert;
  const message = approved ? es.approval.approvedExplanation : rejected ? es.approval.rejectedExplanation
    : isLoading ? es.approval.coverageLoading : !available ? es.approval.coverageUnavailable
    : ready ? es.approval.coverageReady : es.approval.coveragePending;

  return <div className="space-y-5">
    <div className={cn("flex items-start gap-3 rounded-lg p-4 text-sm leading-6", approved || ready ? "bg-success-background text-success-foreground" : rejected ? "bg-destructive/10 text-destructive" : "bg-warning-background text-warning-foreground")}>
      <Icon aria-hidden="true" className="mt-0.5 size-5 shrink-0" />
      <p>{message}</p>
    </div>
    {available && <dl className="grid gap-4 border-b border-border pb-5">
      <div><dt className="text-sm leading-6 text-muted-foreground">{es.approval.reviewedHeats}</dt>
        <dd className="mt-1 text-base leading-6 font-semibold tabular-nums">{es.approval.coverageCount(certificate.heats.length - coverage.pendingHeats.length, certificate.heats.length)}</dd></div>
    </dl>}
  </div>;
}
