export interface CertificateDropzoneProps {
  disabled?: boolean;
  errorId?: string;
  onFilesSelected(files: readonly File[]): void;
}

export function CertificateDropzone({
  disabled = false,
  errorId,
  onFilesSelected,
}: CertificateDropzoneProps) {
  return (
    <label>
      <span>{importTexts.selectFiles}</span>
      <input
        aria-describedby={errorId}
        aria-invalid={errorId ? true : undefined}
        accept=".pdf,.xlsx,application/pdf,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        disabled={disabled}
        multiple
        type="file"
        onChange={(event) =>
          onFilesSelected(Array.from(event.currentTarget.files ?? []))
        }
      />
    </label>
  );
}
import { importTexts } from "../texts";
