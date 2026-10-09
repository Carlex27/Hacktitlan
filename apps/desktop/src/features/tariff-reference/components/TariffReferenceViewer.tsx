import { BookOpenIcon, InfoIcon } from "lucide-react";

import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty";
import { PdfViewer } from "@/features/document-viewer";
import { es } from "@/lib/i18n";

import type { OpenTariffReference } from "../hooks/useTariffReference";

export interface TariffReferenceViewerProps {
  active: OpenTariffReference | null;
}

/** PDF de la LIGIE abierto en la página que indica el backend para el código. */
export function TariffReferenceViewer({ active }: TariffReferenceViewerProps) {
  if (active === null) {
    return (
      <div className="flex h-full items-center justify-center bg-viewer-canvas p-6">
        <Empty className="max-w-sm rounded-lg border border-slate-300 bg-white/90 p-6">
          <EmptyHeader>
            <EmptyMedia variant="icon">
              <BookOpenIcon aria-hidden="true" />
            </EmptyMedia>
            <EmptyTitle>{es.tariffReference.emptyTitle}</EmptyTitle>
            <EmptyDescription>{es.tariffReference.emptyDescription}</EmptyDescription>
          </EmptyHeader>
        </Empty>
      </div>
    );
  }

  const { reference, label } = active;

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex min-w-0 flex-col gap-1.5 border-b border-slate-700/60 bg-viewer-header p-3 text-xs text-slate-200">
        <div className="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1">
          <span className="font-mono font-semibold break-all">{reference.catalogCode ?? label}</span>
          {reference.page !== null && (
            <span className="text-slate-400">· {es.tariffReference.page(reference.page)}</span>
          )}
        </div>
        {reference.sourceText && (
          <p className="max-h-24 overflow-y-auto text-slate-300 break-words whitespace-pre-line">
            {reference.sourceText}
          </p>
        )}
        {reference.legalStatus && (
          <p className="flex items-start gap-1.5 text-[11px] text-amber-300">
            <InfoIcon aria-hidden="true" className="mt-0.5 size-3.5 shrink-0" />
            <span className="min-w-0 break-words">{reference.legalStatus}</span>
          </p>
        )}
      </div>

      {reference.page === null && (
        <p className="bg-amber-50 px-3 py-1.5 text-[11px] text-amber-800">{es.tariffReference.noPage}</p>
      )}
      <div className="min-h-0 flex-1">
        <PdfViewer
          filePath={reference.filePath}
          page={reference.page ?? 1}
          fileName={es.tariffReference.sourceName}
        />
      </div>
    </div>
  );
}
