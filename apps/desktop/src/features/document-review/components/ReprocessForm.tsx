import { RotateCwIcon } from "lucide-react";
import { useId, useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { es } from "@/lib/i18n";

import { validateReprocessForm, type ReprocessFormErrors } from "../model/reviewItem";

export interface ReprocessFormProps {
  /** Deshabilitado si el acta tiene una extracción activa u otra solicitud en curso. */
  disabled: boolean;
  isSubmitting: boolean;
  onSubmit(personName: string, reason: string): Promise<boolean>;
}

export function ReprocessForm({ disabled, isSubmitting, onSubmit }: ReprocessFormProps) {
  const [person, setPerson] = useState("");
  const [reason, setReason] = useState("");
  const [errors, setErrors] = useState<ReprocessFormErrors>({});
  const ids = { person: useId(), reason: useId(), personError: useId(), reasonError: useId(), hint: useId() };
  const locked = disabled || isSubmitting;

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const found = validateReprocessForm(person, reason, es.documentReview);
    setErrors(found);
    if (Object.keys(found).length > 0) return;
    if (await onSubmit(person.trim(), reason.trim())) setReason("");
  }

  return (
    <form onSubmit={handleSubmit} noValidate className="flex flex-col gap-2">
      <fieldset disabled={locked} aria-describedby={ids.hint} className="flex flex-col gap-2">
        <legend className="text-[11px] font-semibold text-slate-700">{es.documentReview.reprocessTitle}</legend>
        <p id={ids.hint} className="text-[11px] text-slate-500">{es.documentReview.reprocessHint}</p>
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          <div className="flex flex-col gap-0.5">
            <label htmlFor={ids.person} className="text-[11px] text-slate-600">{es.documentReview.personLabel}</label>
            <Input
              id={ids.person}
              value={person}
              onChange={(event) => setPerson(event.target.value)}
              aria-invalid={errors.person ? true : undefined}
              aria-describedby={errors.person ? ids.personError : undefined}
              className="h-8 text-xs"
            />
            {errors.person && <p id={ids.personError} className="text-[11px] text-destructive">{errors.person}</p>}
          </div>
          <div className="flex flex-col gap-0.5">
            <label htmlFor={ids.reason} className="text-[11px] text-slate-600">{es.documentReview.reasonLabel}</label>
            <Input
              id={ids.reason}
              value={reason}
              onChange={(event) => setReason(event.target.value)}
              aria-invalid={errors.reason ? true : undefined}
              aria-describedby={errors.reason ? ids.reasonError : undefined}
              className="h-8 text-xs"
            />
            {errors.reason && <p id={ids.reasonError} className="text-[11px] text-destructive">{errors.reason}</p>}
          </div>
        </div>
        <div>
          <Button type="submit" variant="outline" size="sm">
            {isSubmitting ? (
              <Spinner data-icon="inline-start" aria-hidden="true" />
            ) : (
              <RotateCwIcon data-icon="inline-start" aria-hidden="true" />
            )}
            {isSubmitting ? es.documentReview.processing : es.documentReview.reprocess}
          </Button>
        </div>
      </fieldset>
    </form>
  );
}
