import { useId, useState } from "react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { describeApiError, type ClassificationResultDto } from "@/lib/api";
import { es } from "@/lib/i18n";
import { useCandidateSelection } from "../hooks/useCandidateSelection";

export function ManualClassificationForm({ result, disabled, onSaved }: { result: ClassificationResultDto; disabled: boolean; onSaved(): void }) {
  const text = es.classification.manual;
  const fractionId = useId();
  const nicoId = useId();
  const reasonId = useId();
  const errorId = useId();
  const [fraction, setFraction] = useState("");
  const [nico, setNico] = useState("");
  const [reason, setReason] = useState("");
  const [saved, setSaved] = useState(false);
  const { selectManual, isSubmitting, error } = useCandidateSelection();
  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (disabled || isSubmitting) return;
    setSaved(false);
    try {
      await selectManual(result.id, fraction, nico, es.approval.defaultPerson, reason.trim());
      setSaved(true);
      onSaved();
    } catch { /* El hook conserva el error para mostrarlo. */ }
  }
  return <form aria-label={text.title} onSubmit={submit} className="space-y-4 rounded-xl border border-border bg-background p-5">
    <h3 className="text-lg font-semibold">{text.title}</h3>
    <p className="text-sm text-muted-foreground">{text.description}</p>
    {result.current_selection && <p className="text-sm">{text.current}: {result.fraction} · NICO {result.nico}</p>}
    <fieldset disabled={disabled || isSubmitting} className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2">
        <div><label className="mb-2 block text-sm font-medium" htmlFor={fractionId}>{text.fraction}</label>
          <Input className="min-h-11" id={fractionId} inputMode="numeric" pattern="[0-9]{8}" minLength={8} maxLength={8} required value={fraction}
            onChange={(event) => { setFraction(event.target.value); setSaved(false); }} aria-describedby={error ? errorId : undefined} /></div>
        <div><label className="mb-2 block text-sm font-medium" htmlFor={nicoId}>{text.nico}</label>
          <Input className="min-h-11" id={nicoId} inputMode="numeric" pattern="[0-9]{2}" minLength={2} maxLength={2} required value={nico}
            onChange={(event) => { setNico(event.target.value); setSaved(false); }} aria-describedby={error ? errorId : undefined} /></div>
      </div>
      <div><label className="mb-2 block text-sm font-medium" htmlFor={reasonId}>{text.reason}</label>
        <Textarea id={reasonId} required minLength={3} maxLength={4000} value={reason}
          onChange={(event) => { setReason(event.target.value); setSaved(false); }} aria-describedby={error ? errorId : undefined} /></div>
      <div className="flex justify-end">
        <Button type="submit" className="min-h-11">{isSubmitting ? text.saving : text.save}</Button>
      </div>
    </fieldset>
    {saved && <p role="status">{text.saved}</p>}
    {error && <Alert id={errorId} variant="destructive" role="alert"><AlertTitle>{es.approval.errorTitle}</AlertTitle>
      <AlertDescription>{describeApiError(error)}</AlertDescription></Alert>}
  </form>;
}
