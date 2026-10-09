import { Button } from "@/components/ui/button";
import type { CertificateObservationDto } from "@/lib/api";
import { es } from "@/lib/i18n";
import { displayObservationValue } from "../model";
import { VerificationCorrectionForm } from "./VerificationCorrectionForm";

export function FieldVerification({ observation, onGoToPage, onCorrected }: {
  observation: CertificateObservationDto;
  onGoToPage?: ((page: number) => void) | undefined;
  onCorrected?: (() => void) | undefined;
}) {
  const verification = observation.verification;
  const text = es.verification;
  const page = verification?.page_number;
  if (!verification) return <p className="text-muted-foreground">{observation.supersedes_id !== null ? text.corrected : text.pending}</p>;
  return <div className="space-y-2">
    <p className={verification.status === "discrepancy" ? "font-medium text-warning-foreground" : undefined}>
      {text[verification.status]}</p>
    {verification.normalized_value !== null && <p>{text.proposal}: {displayObservationValue(verification.raw_value)} → {verification.normalized_value} {verification.unit}</p>}
    {verification.source_text && <p className="break-words">{text.source}: {verification.source_text}</p>}
    {verification.header_text && <p className="break-words">{text.header}: {verification.header_text}</p>}
    {page !== null && page !== undefined && <div>
      {onGoToPage ? <Button type="button" variant="link" className="min-h-11 px-0"
        onClick={() => onGoToPage(page)}>{text.evidence} · {text.location(page)}</Button>
        : <p>{text.location(page)}</p>}
      <p className="text-xs text-muted-foreground">{verification.source_id} · {verification.header_id}</p>
    </div>}
    {verification.status === "discrepancy" && onCorrected && <details>
      <summary className="min-h-11 cursor-pointer py-2 font-medium focus-visible:outline-2 focus-visible:outline-primary">{text.review}</summary>
      <VerificationCorrectionForm observationId={observation.id} onSaved={onCorrected} />
    </details>}
  </div>;
}
