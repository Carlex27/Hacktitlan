import { Check, MessageSquare, User, X } from "lucide-react";
import { useId, useState } from "react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { describeApiError, type ClassificationRunDto } from "@/lib/api";
import { es } from "@/lib/i18n";

import { useRunApproval } from "../hooks/useRunApproval";

export interface ApprovalBarProps {
  run: ClassificationRunDto | null;
  onDecisionComplete?: () => void;
}

export function ApprovalBar({ run, onDecisionComplete }: ApprovalBarProps) {
  const { approveRun, rejectRun, isSubmitting, error, clearError } = useRunApproval();
  const [personName, setPersonName] = useState("");
  const [reason, setReason] = useState("");
  const [validationErrors, setValidationErrors] = useState<{ person?: string; reason?: string }>({});

  const personInputId = useId();
  const reasonInputId = useId();
  const personErrId = useId();
  const reasonErrId = useId();

  if (!run) return null;

  function validate(): boolean {
    const errs: { person?: string; reason?: string } = {};
    if (personName.trim().length < 2) {
      errs.person = es.approval.personRequired;
    }
    if (reason.trim().length < 3) {
      errs.reason = es.approval.reasonRequired;
    }
    setValidationErrors(errs);
    return Object.keys(errs).length === 0;
  }

  async function handleApprove() {
    if (!run) return;
    clearError();
    if (!validate()) return;
    try {
      await approveRun(run.id, personName.trim(), reason.trim());
      setReason("");
      onDecisionComplete?.();
    } catch {
      // error is handled in hook
    }
  }

  async function handleReject() {
    if (!run) return;
    clearError();
    if (!validate()) return;
    try {
      await rejectRun(run.id, personName.trim(), reason.trim());
      setReason("");
      onDecisionComplete?.();
    } catch {
      // error is handled in hook
    }
  }

  const isApproved = run.approval_status === "approved";
  const isRejected = run.approval_status === "rejected";

  return (
    <footer className="bg-white border-t border-slate-200 px-4 py-2.5 flex flex-col gap-2 shrink-0">
      {error && (
        <Alert variant="destructive" role="alert" className="py-2 text-xs">
          <AlertTitle className="text-xs font-semibold">Error al dictaminar</AlertTitle>
          <AlertDescription className="text-xs">{describeApiError(error)}</AlertDescription>
        </Alert>
      )}

      {run.results.length > 1 && (
        <p className="text-[11px] text-slate-500">
          {es.approval.appliesToAllProducts(run.results.length)}
        </p>
      )}

      <div className="flex flex-wrap items-center justify-between gap-3">
        {/* Input fields for Person & Reason (Audit Requirement) */}
        <div className="flex flex-1 items-center gap-3 min-w-[320px]">
          {/* Person Input */}
          <div className="flex-1 max-w-xs relative">
            <User aria-hidden="true" className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-slate-400" />
            <Input
              id={personInputId}
              value={personName}
              onChange={(e) => {
                setPersonName(e.target.value);
                if (validationErrors.person) {
                  setValidationErrors((v) => {
                    const next = { ...v };
                    delete next.person;
                    return next;
                  });
                }
              }}
              placeholder={es.approval.personPlaceholder}
              disabled={isSubmitting}
              aria-invalid={Boolean(validationErrors.person)}
              aria-describedby={validationErrors.person ? personErrId : undefined}
              className="h-8 text-xs pl-8 bg-white"
            />
            {validationErrors.person && (
              <p id={personErrId} role="alert" className="text-[10px] text-red-600 mt-0.5 absolute">
                {validationErrors.person}
              </p>
            )}
          </div>

          {/* Reason / Comments Input */}
          <div className="flex-1 relative">
            <MessageSquare aria-hidden="true" className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-slate-400" />
            <Input
              id={reasonInputId}
              value={reason}
              onChange={(e) => {
                setReason(e.target.value);
                if (validationErrors.reason) {
                  setValidationErrors((v) => {
                    const next = { ...v };
                    delete next.reason;
                    return next;
                  });
                }
              }}
              placeholder={es.approval.reasonPlaceholder}
              disabled={isSubmitting}
              aria-invalid={Boolean(validationErrors.reason)}
              aria-describedby={validationErrors.reason ? reasonErrId : undefined}
              className="h-8 text-xs pl-8 bg-white"
            />
            {validationErrors.reason && (
              <p id={reasonErrId} role="alert" className="text-[10px] text-red-600 mt-0.5 absolute">
                {validationErrors.reason}
              </p>
            )}
          </div>
        </div>

        {/* Status Badge & Actions */}
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1.5 text-xs text-slate-500 mr-2">
            <span>{es.approval.statusBadge}</span>
            <Badge
              variant={isApproved ? "default" : isRejected ? "destructive" : "outline"}
              className="text-[10px]"
            >
              {run.approval_status}
            </Badge>
          </div>

          {/* Reject Button */}
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={handleReject}
            disabled={isSubmitting}
            className="border-red-200 text-red-600 hover:bg-red-50 hover:text-red-700 h-8 text-xs"
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
            disabled={isSubmitting}
            className="bg-emerald-600 hover:bg-emerald-700 text-white h-8 text-xs"
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
