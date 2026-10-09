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
  return <li className="grid min-w-0 gap-3 py-5 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center lg:grid-cols-[minmax(0,1fr)_9rem_auto] lg:gap-6">
    <div className="min-w-0 space-y-1">
      <h4 className="text-base leading-6 font-semibold break-words">{number}</h4>
      <p className="text-sm leading-5 text-muted-foreground break-words">{manufacturer ?? es.workspace.unknown}</p>
    </div>
    <p className="text-sm leading-5 text-muted-foreground sm:col-start-1 sm:row-start-2 lg:col-start-2 lg:row-start-1">
      <span className="lg:block">{es.workspace.date}: </span><span className="tabular-nums lg:text-foreground">{date ?? es.workspace.unknown}</span>
    </p>
    <div className="flex flex-wrap items-center justify-between gap-3 sm:col-start-2 sm:row-start-1 sm:row-span-2 sm:justify-end lg:col-start-3 lg:row-span-1">
      <Badge variant={status === "rejected" ? "destructive" : "secondary"} className={`h-auto min-h-7 max-w-full gap-1.5 whitespace-normal px-3 py-1 text-xs leading-5 ${status === "needs_review" ? "border-warning-border bg-warning-background text-warning-foreground" : status === "approved" ? "bg-success-background text-success-foreground" : ""}`}>
        <StatusIcon aria-hidden="true" />{es.workspace.status[status]}
      </Badge>
      <Button variant="outline" className="min-h-11 shrink-0" onClick={onReview}>
        {es.savedCertificates.review}<ArrowRight aria-hidden="true" />
      </Button>
    </div>
  </li>;
}
