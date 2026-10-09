import { Download, FileSpreadsheet } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { LoadErrorAlert } from "@/components/feedback";
import { es } from "@/lib/i18n";
import { useCertificateExport } from "./useCertificateExport";

export function CertificateExportButton({ certificateId, disabled = false }: {
  certificateId: number; disabled?: boolean;
}) {
  const report = useCertificateExport(certificateId);
  return <div className="min-w-0 space-y-2">
    <div className="flex flex-wrap gap-2">
      <Button type="button" variant="outline" className="min-h-11" disabled={disabled || report.state === "loading"}
        onClick={() => void report.generate()} title={es.certificateExport.hint}>
        {report.state === "loading" ? <Spinner aria-hidden="true" /> : <FileSpreadsheet aria-hidden="true" />}
        <span aria-live="polite">{report.state === "loading" ? es.certificateExport.loading : es.certificateExport.generate}</span>
      </Button>
      {report.downloadUrl && <Button asChild variant="outline" className="min-h-11">
        <a href={report.downloadUrl} download><Download aria-hidden="true" />{es.certificateExport.download}</a>
      </Button>}
    </div>
    {report.state === "success" && <p role="status" className="text-xs text-muted-foreground">{es.certificateExport.ready}</p>}
    {report.error !== null && <LoadErrorAlert title={es.certificateExport.failed} error={report.error} />}
  </div>;
}
