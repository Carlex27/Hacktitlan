import { FileUpIcon } from "lucide-react";
import { useId, useState, type DragEvent } from "react";

import { cn } from "@/lib/utils";
import { es } from "@/lib/i18n";
import { buttonVariants } from "@/components/ui/button";

import { partitionPdfFiles } from "../model/partitionPdfFiles";

export interface CertificateDropzoneProps {
  disabled?: boolean;
  errorId?: string;
  onFilesSelected(files: readonly File[]): void;
}

export function CertificateDropzone({
  disabled = false,
  errorId: externalErrorId,
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
          "group flex cursor-pointer flex-wrap items-center justify-between gap-6 rounded-xl border border-dashed border-input bg-muted/30 p-6 sm:p-8 text-foreground transition-colors",
          "hover:bg-muted/60 hover:border-primary has-focus-visible:outline-2 has-focus-visible:outline-offset-4 has-focus-visible:outline-primary",
          "data-dragging:border-primary data-dragging:bg-muted",
          "data-disabled:cursor-not-allowed data-disabled:opacity-50",
        )}
      >
        <div className="flex items-center gap-2.5 min-w-0">
          <div className="size-12 rounded-lg bg-muted flex items-center justify-center text-foreground shrink-0">
            <FileUpIcon aria-hidden="true" className="size-6" />
          </div>
          <div className="flex flex-col text-left min-w-0">
            <span className="text-base leading-6 font-semibold">
              {es.certificateImport.dropzone.label}
            </span>
            <span id={hintId} className="text-sm leading-5 text-muted-foreground">
              {es.certificateImport.dropzone.hint}
            </span>
          </div>
        </div>

        <span className={cn(buttonVariants({ variant: "default", size: "lg" }), "min-h-11 px-4 group-hover:bg-primary/80")}>
          {es.certificateImport.dropzone.browse}
        </span>

        <input
          id={inputId}
          className="sr-only"
          type="file"
          accept=".pdf,.xlsx,application/pdf,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
          multiple
          disabled={disabled}
          aria-describedby={[hintId, hasError ? errorId : undefined, externalErrorId].filter(Boolean).join(" ")}
          aria-invalid={hasError || !!externalErrorId || undefined}
          onChange={(event) => {
            handleFiles(Array.from(event.currentTarget.files ?? []));
            event.currentTarget.value = "";
          }}
        />
      </label>
      {hasError && (
        <p id={errorId} role="alert" className="mt-2 text-sm leading-5 text-destructive font-medium">
          {es.certificateImport.dropzone.rejected(rejected)}
        </p>
      )}
    </div>
  );
}
