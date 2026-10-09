import { useId, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { describeApiError } from "@/lib/api";
import { es } from "@/lib/i18n";
import { useVerificationCorrection } from "../hooks/useVerificationCorrection";

export function VerificationCorrectionForm({ observationId, onSaved }: { observationId: number; onSaved(): void }) {
  const id = useId();
  const text = es.verification;
  const [person, setPerson] = useState("");
  const [reason, setReason] = useState("");
  const correction = useVerificationCorrection(observationId);
  return <form className="space-y-3" onSubmit={async (event) => {
    event.preventDefault();
    if (await correction.accept(person.trim(), reason.trim())) onSaved();
  }}>
    <fieldset className="space-y-3" disabled={correction.isSaving || correction.saved}>
      <div><label className="block font-medium" htmlFor={`${id}-person`}>{text.person}</label>
        <Input id={`${id}-person`} required minLength={2} maxLength={200} value={person}
          onChange={(event) => setPerson(event.target.value)} aria-describedby={correction.error ? `${id}-error` : undefined} /></div>
      <div><label className="block font-medium" htmlFor={`${id}-reason`}>{text.reason}</label>
        <Textarea id={`${id}-reason`} required minLength={3} maxLength={4000} value={reason}
          onChange={(event) => setReason(event.target.value)} aria-describedby={correction.error ? `${id}-error` : undefined} /></div>
      <Button type="submit" className="min-h-11">{correction.isSaving ? text.saving : text.accept}</Button>
    </fieldset>
    {correction.error !== null && <p id={`${id}-error`} role="alert" className="break-words text-destructive">{describeApiError(correction.error)}</p>}
    {correction.saved && <p role="status">{text.saved}</p>}
  </form>;
}
