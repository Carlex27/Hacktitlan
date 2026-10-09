import { ExternalLink, FileText, RefreshCw } from "lucide-react";
import { useState } from "react";

import { Empty, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from "@/components/ui/empty";
import { es } from "@/lib/i18n";
import { cn } from "@/lib/utils";

export interface PdfViewerProps {
  fileUrl: string | null;
  page?: number;
  fileName?: string | null;
  className?: string;
}

export function PdfViewer({ fileUrl, page = 1, fileName, className }: PdfViewerProps) {
  const [reloadKey, setReloadKey] = useState(0);

  if (!fileUrl) {
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

  const iframeSrc = `${fileUrl}#page=${page}`;

  return (
    <div className={cn("flex flex-col w-full h-full bg-viewer-bg min-h-0", className)}>
      {/* Header Bar */}
      <div className="h-9 bg-viewer-header px-3 flex items-center justify-between border-b border-slate-700/60 shrink-0">
        <div className="flex items-center gap-2 min-w-0">
          <span className="bg-red-500 text-white rounded text-[10px] font-bold px-1.5 py-0.5 leading-tight shrink-0 select-none">
            {es.viewer.pdfBadge}
          </span>
          <span
            className="text-xs font-medium text-slate-200 truncate"
            title={fileName ?? es.viewer.title}
          >
            {fileName ?? es.viewer.title}
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
            onClick={() => setReloadKey((k) => k + 1)}
            className="hover:text-white p-1 hover:bg-slate-700/50 rounded transition-colors select-none"
            title={es.viewer.reload}
          >
            <RefreshCw aria-hidden="true" className="w-3.5 h-3.5" />
          </button>
          <a
            href={fileUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-white p-1 hover:bg-slate-700/50 rounded transition-colors select-none"
            title={es.viewer.openNewTab}
          >
            <ExternalLink aria-hidden="true" className="w-3.5 h-3.5" />
          </a>
        </div>
      </div>

      {/* Document Area */}
      <div className="flex-1 bg-viewer-canvas p-2 flex items-center justify-center overflow-hidden min-h-0">
        <iframe
          key={reloadKey}
          src={iframeSrc}
          title={fileName ?? es.viewer.title}
          className="w-full h-full border border-slate-400/30 rounded bg-white"
        />
      </div>
    </div>
  );
}
