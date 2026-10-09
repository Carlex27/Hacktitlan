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
      <div className="bg-white p-3.5 rounded-lg border border-slate-200 shadow-sm space-y-3">
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
      <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-sm">
        <Empty>
          <EmptyHeader>
            <EmptyMedia variant="icon">
              <FileText aria-hidden="true" className="w-6 h-6 text-slate-400" />
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
      .join(", ") || "Sin registrar";

  return (
    <section
      className="bg-white p-3.5 rounded-lg border border-slate-200 shadow-sm"
      aria-labelledby="cert-summary-title"
    >
      <div className="flex items-center justify-between mb-3 border-b border-slate-100 pb-2">
        <h3 id="cert-summary-title" className="font-bold text-slate-800 text-[13px]">
          {es.certificateReview.summaryTitle}
        </h3>
        <Badge variant={certificate.approval_status === "approved" ? "default" : "outline"}>
          {certificate.approval_status}
        </Badge>
      </div>

      <div className="grid grid-cols-2 gap-x-5 gap-y-2.5 text-xs">
        <div>
          <span className="block text-[11px] font-medium text-slate-500 mb-0.5">
            {es.certificateReview.fields.manufacturer}
          </span>
          <div className="font-medium text-slate-800 bg-slate-50/70 border border-slate-200 rounded px-2.5 py-1.5 truncate">
            {certificate.manufacturer ?? "Sin dato"}
          </div>
        </div>

        <div>
          <span className="block text-[11px] font-medium text-slate-500 mb-0.5">
            {es.certificateReview.fields.certificateNo}
          </span>
          <div className="font-medium text-slate-800 bg-slate-50/70 border border-slate-200 rounded px-2.5 py-1.5 truncate">
            {certificate.certificate_no ?? "Sin dato"}
          </div>
        </div>

        <div>
          <span className="block text-[11px] font-medium text-slate-500 mb-0.5">
            {es.certificateReview.fields.certificateDate}
          </span>
          <div className="font-medium text-slate-800 bg-slate-50/70 border border-slate-200 rounded px-2.5 py-1.5">
            {certificate.certificate_date ?? "Sin dato"}
          </div>
        </div>

        <div>
          <span className="block text-[11px] font-medium text-slate-500 mb-0.5">
            {es.certificateReview.fields.standard}
          </span>
          <div className="font-medium text-slate-800 bg-slate-50/70 border border-slate-200 rounded px-2.5 py-1.5 truncate">
            {certificate.standard ?? "Sin dato"}
          </div>
        </div>

        <div>
          <span className="block text-[11px] font-medium text-slate-500 mb-0.5">
            {es.certificateReview.fields.productName}
          </span>
          <div className="font-medium text-slate-800 bg-slate-50/70 border border-slate-200 rounded px-2.5 py-1.5 truncate">
            {certificate.product_name ?? "Sin dato"}
          </div>
        </div>

        <div>
          <span className="block text-[11px] font-medium text-slate-500 mb-0.5">Coladas registradas</span>
          <div className="font-medium text-slate-800 bg-slate-50/70 border border-slate-200 rounded px-2.5 py-1.5 truncate">
            {heatsText}
          </div>
        </div>
      </div>

      {certificate.demo_notice && (
        <p className="mt-2 text-[10.5px] text-amber-700 bg-amber-50/80 border border-amber-200 rounded px-2 py-1">
          {certificate.demo_notice}
        </p>
      )}
    </section>
  );
}
