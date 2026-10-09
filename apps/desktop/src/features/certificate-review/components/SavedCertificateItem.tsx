import { ArrowRight, CircleCheck, CircleX, Clock, FileText } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { es } from "@/lib/i18n";

interface SavedCertificateItemProps {
  number: string;
  manufacturer: string | null;
  date: string | null;
  status: keyof typeof es.workspace.status;
  onReview(): void;
}

export function SavedCertificateItem({ number, manufacturer, date, status, onReview }: SavedCertificateItemProps) {
  const StatusIcon = status === "approved" ? CircleCheck : status === "rejected" ? CircleX : status === "needs_review" ? Clock : FileText;
  return <li className="flex flex-wrap items-center justify-between gap-4 py-5">
    <div className="min-w-0 flex-1 basis-56 space-y-2">
      <p className="text-base leading-6 font-semibold break-words">{number}</p>
      <p className="text-sm leading-5 text-muted-foreground break-words">{manufacturer ?? es.workspace.unknown}</p>
      <p className="text-sm leading-5 text-muted-foreground">{es.workspace.date}: <span className="tabular-nums">{date ?? es.workspace.unknown}</span></p>
    </div>
    <div className="flex flex-wrap items-center gap-3">
      <Badge variant={status === "rejected" ? "destructive" : "secondary"} className="h-auto max-w-full gap-1.5 whitespace-normal py-1 text-sm leading-5">
        <StatusIcon aria-hidden="true" />{es.workspace.status[status]}
      </Badge>
      <Button variant="outline" className="min-h-10" onClick={onReview}>
        {es.savedCertificates.review}<ArrowRight aria-hidden="true" />
      </Button>
    </div>
  </li>;
}
