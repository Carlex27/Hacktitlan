export interface CertificateDropzoneProps {
  disabled?: boolean;
  onFilesSelected(files: readonly File[]): void;
}

export function CertificateDropzone({
  disabled = false,
  onFilesSelected,
}: CertificateDropzoneProps) {
  return (
    <label>
      <span>Seleccionar certificados PDF</span>
      <input
        accept="application/pdf"
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
