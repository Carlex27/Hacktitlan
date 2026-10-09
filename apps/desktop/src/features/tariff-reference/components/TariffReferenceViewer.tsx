import { BookOpenIcon, InfoIcon } from "lucide-react";

import { LoadErrorAlert } from "@/components/feedback";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty";
import { Spinner } from "@/components/ui/spinner";
import { PdfViewer } from "@/features/document-viewer";
import { es } from "@/lib/i18n";
import { cn } from "@/lib/utils";

import type { TariffReferenceState } from "../hooks/useTariffReference";
import { isReferenceUnsupported } from "../model/referenceSupport";

export interface TariffReferenceViewerProps {
  state: TariffReferenceState;
  onRetry(): void;
  onSelectEntry(index: number): void;
}

/** PDF de la LIGIE abierto en la página del código consultado. */
export function TariffReferenceViewer({ state, onRetry, onSelectEntry }: TariffReferenceViewerProps) {
  if (state.status === "idle") {
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

  if (state.status === "loading") {
    return (
      <div role="status" className="flex h-full items-center justify-center gap-2 bg-viewer-canvas text-xs text-slate-200">
        <Spinner aria-hidden="true" />
        {es.tariffReference.loading(state.label)}
      </div>
    );
  }

  if (state.status === "error") {
    return (
      <div className="p-4">
        {isReferenceUnsupported(state.error) ? (
          <Alert role="alert">
            <InfoIcon aria-hidden="true" />
            <AlertTitle>{es.tariffReference.unsupportedTitle}</AlertTitle>
            <AlertDescription className="flex flex-col items-start gap-2">
              <p>{es.tariffReference.unsupportedDescription}</p>
              <Button type="button" variant="outline" size="sm" onClick={onRetry}>
                {es.feedback.retry}
              </Button>
            </AlertDescription>
          </Alert>
        ) : (
          <LoadErrorAlert title={es.tariffReference.loadError} error={state.error} onRetry={onRetry} />
        )}
      </div>
    );
  }

  const { entries, meta, activeIndex } = state;
  const entry = entries[activeIndex] ?? entries[0];
  if (!entry) return null;

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex flex-col gap-2 border-b border-slate-700/60 bg-viewer-header p-3 text-xs text-slate-200">
        <div className="flex items-center gap-2">
          <Badge variant="secondary">{es.tariffReference.kind[entry.kind]}</Badge>
          <span className="font-mono font-semibold">{entry.code}</span>
          {entry.page !== null && (
            <span className="text-slate-400">· {es.tariffReference.page(entry.page)}</span>
          )}
        </div>
        <p className="text-slate-300">{entry.description}</p>

        {entries.length > 1 && (
          <div className="flex flex-col gap-1.5">
            <p className="text-amber-300">{es.tariffReference.duplicates(entries.length)}</p>
            <ul className="flex flex-col gap-1">
              {entries.map((candidate, index) => (
                <li key={`${candidate.code}-${index}`}>
                  <button
                    type="button"
                    aria-pressed={index === activeIndex}
                    onClick={() => onSelectEntry(index)}
                    className={cn(
                      "w-full rounded border px-2 py-1 text-left transition-colors",
                      "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-400",
                      index === activeIndex
                        ? "border-blue-400 bg-blue-500/20"
                        : "border-slate-600 hover:bg-slate-700/50",
                    )}
                  >
                    {candidate.page !== null && `${es.tariffReference.page(candidate.page)} · `}
                    {candidate.description}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}

        <p className="flex items-start gap-1.5 text-[11px] text-slate-400">
          <InfoIcon aria-hidden="true" className="mt-0.5 size-3.5 shrink-0" />
          {meta.notice}
        </p>
      </div>

      {meta.file_status.available ? (
        <>
          {entry.page === null && (
            <p className="bg-amber-50 px-3 py-1.5 text-[11px] text-amber-800">{es.tariffReference.noPage}</p>
          )}
          <div className="min-h-0 flex-1">
            <PdfViewer
              filePath={meta.file_url}
              page={entry.page ?? 1}
              fileName={meta.source}
            />
          </div>
        </>
      ) : (
        <div className="p-4">
          <Alert variant="destructive" role="alert">
            <AlertTitle>{es.tariffReference.fileUnavailable}</AlertTitle>
            <AlertDescription>{meta.file_status.message}</AlertDescription>
          </Alert>
        </div>
      )}
    </div>
  );
}
