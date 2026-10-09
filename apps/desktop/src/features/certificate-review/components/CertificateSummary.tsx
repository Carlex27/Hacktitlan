import { FileText } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Empty, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from "@/components/ui/empty";
import { Skeleton } from "@/components/ui/skeleton";
import type { CertificateDetailDto } from "@/lib/api";
import { es } from "@/lib/i18n";

export interface CertificateSummaryProps {
  certificate: CertificateDetailDto | null;
  isLoading?: boolean;
}

export function CertificateSummary({ certificate, isLoading = false }: CertificateSummaryProps) {
  if (isLoading) {
    return (
      <div className="bg-background p-5 rounded-xl border border-border space-y-3">
        <div className="flex justify-between items-center">
          <Skeleton className="h-4 w-36" />
          <Skeleton className="h-4 w-16" />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <Skeleton className="h-12 w-full" />
          <Skeleton className="h-12 w-full" />
          <Skeleton className="h-12 w-full" />
          <Skeleton className="h-12 w-full" />
        </div>
      </div>
    );
  }

  if (!certificate) {
    return (
      <div className="bg-background p-4 rounded-xl border border-border">
        <Empty>
          <EmptyHeader>
            <EmptyMedia variant="icon">
              <FileText aria-hidden="true" className="w-6 h-6 text-muted-foreground" />
            </EmptyMedia>
            <EmptyTitle>{es.certificateReview.summaryTitle}</EmptyTitle>
            <EmptyDescription>{es.certificateReview.noCertificateSelected}</EmptyDescription>
          </EmptyHeader>
        </Empty>
      </div>
    );
  }

  const heatsText =
    certificate.heats
      .map((h) => h.heat_no)
      .filter(Boolean)
      .join(", ") || es.workspace.unknown;

  return (
    <section
      className="bg-background p-5 rounded-xl border border-border"
      aria-labelledby="cert-summary-title"
    >
      <div className="flex flex-wrap items-center justify-between gap-3 mb-4 border-b border-border pb-4">
        <h3 id="cert-summary-title" className="font-semibold text-foreground text-lg leading-7">
          {es.certificateReview.summaryTitle}
        </h3>
        <Badge variant={certificate.approval_status === "approved" ? "default" : "outline"}>
          {es.workspace.status[certificate.approval_status]}
        </Badge>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-4 text-sm leading-6">
        <div>
          <span className="block text-sm font-medium text-muted-foreground mb-1">
            {es.certificateReview.fields.manufacturer}
          </span>
          <div className="font-medium text-foreground break-words">
            {certificate.manufacturer ?? es.workspace.unknown}
          </div>
        </div>

        <div>
          <span className="block text-sm font-medium text-muted-foreground mb-1">
            {es.certificateReview.fields.certificateNo}
          </span>
          <div className="font-medium text-foreground break-words">
            {certificate.certificate_no ?? es.workspace.unknown}
          </div>
        </div>

        <div>
          <span className="block text-sm font-medium text-muted-foreground mb-1">
            {es.certificateReview.fields.certificateDate}
          </span>
          <div className="font-medium text-foreground">
            {certificate.certificate_date ?? es.workspace.unknown}
          </div>
        </div>

        <div>
          <span className="block text-sm font-medium text-muted-foreground mb-1">
            {es.certificateReview.fields.standard}
          </span>
          <div className="font-medium text-foreground break-words">
            {certificate.standard ?? es.workspace.unknown}
          </div>
        </div>

        <div>
          <span className="block text-sm font-medium text-muted-foreground mb-1">
            {es.certificateReview.fields.productName}
          </span>
          <div className="font-medium text-foreground break-words">
            {certificate.product_name ?? es.workspace.unknown}
          </div>
        </div>

        <div>
          <span className="block text-sm font-medium text-muted-foreground mb-1">{es.workspace.registeredHeats}</span>
          <div className="font-medium text-foreground break-words">
            {heatsText}
          </div>
        </div>
      </div>

    </section>
  );
}
