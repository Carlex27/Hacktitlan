import { FileText } from "lucide-react";

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
      {/* Document Area */}
      <div className="flex-1 bg-viewer-canvas flex items-center justify-center overflow-hidden min-h-0">
        {state.status === "ready" && state.isPdf && (
          <iframe
            key={`${state.objectUrl}#page=${page}`}
            src={`${state.objectUrl}#page=${page}`}
            title={title}
            className="w-full h-full border-0 bg-white"
          />
        )}
        {state.status === "ready" && !state.isPdf && <div className="rounded-lg bg-white p-6 text-sm space-y-4">
          <p>{es.workspace.spreadsheetNotice}</p>
          <a href={api.url(filePath ?? "")} className="underline text-blue-700 focus-visible:outline-2 focus-visible:outline-blue-600">{es.workspace.downloadOriginal}</a>
        </div>}
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
