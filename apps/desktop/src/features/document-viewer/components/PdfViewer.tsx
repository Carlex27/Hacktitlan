import { ExternalLink, FileText, RefreshCw } from "lucide-react";

import { LoadErrorAlert } from "@/components/feedback";
import { Empty, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from "@/components/ui/empty";
import { Spinner } from "@/components/ui/spinner";
import { useApiClient } from "@/lib/api";
import { es } from "@/lib/i18n";
import { cn } from "@/lib/utils";

import { usePdfObjectUrl } from "../hooks/usePdfObjectUrl";

export interface PdfViewerProps {
  /** Ruta del PDF en el API (p. ej. `/api/v1/documents/10/file`); `null` sin documento. */
  filePath: string | null;
  page?: number;
  fileName?: string | null;
  className?: string;
}

export function PdfViewer({ filePath, page = 1, fileName, className }: PdfViewerProps) {
  const api = useApiClient();
  const { state, reload } = usePdfObjectUrl(filePath);

  if (filePath === null) {
    return (
      <div
        className={cn(
          "w-full h-full flex items-center justify-center bg-viewer-canvas p-6",
          className,
        )}
      >
        <Empty className="bg-white/90 border border-slate-300 rounded-lg p-6 max-w-sm">
          <EmptyHeader>
            <EmptyMedia variant="icon">
              <FileText aria-hidden="true" className="w-8 h-8 text-slate-400" />
            </EmptyMedia>
            <EmptyTitle>{es.viewer.emptyTitle}</EmptyTitle>
            <EmptyDescription>{es.viewer.emptyDescription}</EmptyDescription>
          </EmptyHeader>
        </Empty>
      </div>
    );
  }

  const title = fileName ?? es.viewer.title;

  return (
    <div className={cn("flex flex-col w-full h-full bg-viewer-bg min-h-0", className)}>
      {/* Header Bar */}
      <div className="h-9 bg-viewer-header px-3 flex items-center justify-between border-b border-slate-700/60 shrink-0">
        <div className="flex items-center gap-2 min-w-0">
          <span className="bg-red-500 text-white rounded text-[10px] font-bold px-1.5 py-0.5 leading-tight shrink-0 select-none">
            {es.viewer.pdfBadge}
          </span>
          <span className="text-xs font-medium text-slate-200 truncate" title={title}>
            {title}
          </span>
        </div>
      </div>

      {/* Toolbar */}
      <div className="h-9 bg-viewer-toolbar px-3 flex items-center justify-between text-slate-300 text-xs border-b border-slate-800 shrink-0">
        <div className="flex items-center gap-2 text-[11px] font-medium text-slate-300 select-none">
          <span>{es.viewer.page} {page}</span>
        </div>

        <div className="flex items-center gap-1.5">
          <button
            type="button"
            onClick={reload}
            className="hover:text-white p-1 hover:bg-slate-700/50 rounded transition-colors select-none"
            title={es.viewer.reload}
            aria-label={es.viewer.reload}
          >
            <RefreshCw aria-hidden="true" className="w-3.5 h-3.5" />
          </button>
          <a
            href={api.url(filePath)}
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-white p-1 hover:bg-slate-700/50 rounded transition-colors select-none"
            title={es.viewer.openNewTab}
            aria-label={es.viewer.openNewTab}
          >
            <ExternalLink aria-hidden="true" className="w-3.5 h-3.5" />
          </a>
        </div>
      </div>

      {/* Document Area */}
      <div className="flex-1 bg-viewer-canvas p-2 flex items-center justify-center overflow-hidden min-h-0">
        {state.status === "ready" && (
          <iframe
            src={`${state.objectUrl}#page=${page}`}
            title={title}
            className="w-full h-full border border-slate-400/30 rounded bg-white"
          />
        )}
        {(state.status === "loading" || state.status === "idle") && (
          <div role="status" className="flex items-center gap-2 text-xs text-slate-200">
            <Spinner aria-hidden="true" />
            {es.viewer.loading}
          </div>
        )}
        {state.status === "error" && (
          <div className="w-full max-w-md">
            <LoadErrorAlert title={es.viewer.loadError} error={state.error} onRetry={reload} />
          </div>
        )}
      </div>
    </div>
  );
}
