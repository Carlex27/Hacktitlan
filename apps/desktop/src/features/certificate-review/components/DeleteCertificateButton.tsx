import { Trash2 } from "lucide-react";
import { LoadErrorAlert } from "@/components/feedback";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { es } from "@/lib/i18n";
import { useCertificateDeletion } from "../hooks/useCertificateDeletion";

export function DeleteCertificateButton({ certificateId, onDeleted }: {
  certificateId: number;
  onDeleted(): void;
}) {
  const state = useCertificateDeletion(certificateId);
  const remove = async () => { if (await state.remove()) onDeleted(); };
  return <div className="min-w-0 space-y-2">
    <Button type="button" variant="destructive" className="min-h-10" disabled={state.isDeleting}
      title={es.certificateDeletion.hint} onClick={() => void remove()}>
      {state.isDeleting ? <Spinner aria-hidden="true" /> : <Trash2 aria-hidden="true" />}
      <span aria-live="polite">{state.isDeleting ? es.certificateDeletion.deleting : es.certificateDeletion.button}</span>
    </Button>
    {state.error !== null && <LoadErrorAlert title={es.certificateDeletion.error} error={state.error} />}
  </div>;
}
