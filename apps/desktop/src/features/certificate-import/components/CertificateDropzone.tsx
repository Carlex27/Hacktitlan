import { FileUpIcon } from "lucide-react";
import { useId, useState, type DragEvent } from "react";

import { cn } from "@/lib/utils";
import { es } from "@/lib/i18n";

import { partitionPdfFiles } from "../model/partitionPdfFiles";

export interface CertificateDropzoneProps {
  disabled?: boolean;
  onFilesSelected(files: readonly File[]): void;
}

export function CertificateDropzone({
  disabled = false,
  onFilesSelected,
}: CertificateDropzoneProps) {
  const inputId = useId();
  const hintId = useId();
  const errorId = useId();
  const [isDragging, setIsDragging] = useState(false);
  const [rejected, setRejected] = useState<readonly string[]>([]);

  function handleFiles(files: readonly File[]) {
    const { accepted, rejected: invalid } = partitionPdfFiles(files);
    setRejected(invalid.map((file) => file.name));
    if (accepted.length > 0) onFilesSelected(accepted);
  }

  function handleDrop(event: DragEvent<HTMLLabelElement>) {
    event.preventDefault();
    setIsDragging(false);
    if (!disabled) handleFiles(Array.from(event.dataTransfer.files));
  }

  const hasError = rejected.length > 0;

  return (
    <div className="w-full">
      <label
        htmlFor={inputId}
        data-dragging={isDragging || undefined}
        data-disabled={disabled || undefined}
        onDragOver={(event) => {
          event.preventDefault();
          if (!disabled) setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        className={cn(
          "group flex cursor-pointer items-center justify-between gap-3 rounded-lg border border-dashed border-slate-600 bg-[#1e2638] px-3.5 py-2 text-slate-200 transition-all shadow-sm",
          "hover:bg-[#253047] hover:border-blue-400 has-focus-visible:ring-2 has-focus-visible:ring-blue-500",
          "data-dragging:border-blue-400 data-dragging:bg-[#253047]",
          "data-disabled:cursor-not-allowed data-disabled:opacity-50",
        )}
      >
        <div className="flex items-center gap-2.5 min-w-0">
          <div className="w-7 h-7 rounded-md bg-blue-500/20 border border-blue-400/30 flex items-center justify-center text-blue-400 shrink-0 group-hover:scale-105 transition-transform">
            <FileUpIcon aria-hidden="true" className="w-3.5 h-3.5" />
          </div>
          <div className="flex flex-col text-left min-w-0">
            <span className="text-xs font-semibold text-slate-100 truncate">
              {es.certificateImport.dropzone.label}
            </span>
            <span id={hintId} className="text-[10.5px] text-slate-400 truncate">
              {es.certificateImport.dropzone.hint}
            </span>
          </div>
        </div>

        <span className="shrink-0 text-[11px] font-medium px-2 py-0.5 rounded bg-blue-600/30 border border-blue-500/40 text-blue-300 group-hover:bg-blue-600 group-hover:text-white transition-colors">
          Examinar
        </span>

        <input
          id={inputId}
          className="sr-only"
          type="file"
          accept="application/pdf,.pdf"
          multiple
          disabled={disabled}
          aria-describedby={hasError ? `${hintId} ${errorId}` : hintId}
          aria-invalid={hasError || undefined}
          onChange={(event) => {
            handleFiles(Array.from(event.currentTarget.files ?? []));
            event.currentTarget.value = "";
          }}
        />
      </label>
      {hasError && (
        <p id={errorId} role="alert" className="mt-1 text-xs text-red-400 font-medium">
          {es.certificateImport.dropzone.rejected(rejected)}
        </p>
      )}
    </div>
  );
}
