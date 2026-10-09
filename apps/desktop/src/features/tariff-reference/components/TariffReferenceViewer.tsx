import { BookOpenIcon } from "lucide-react";

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

  const { reference } = active;

  return (
    <div className="flex h-full min-h-0 flex-col">
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
