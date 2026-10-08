import { CertificateDropzone, ImportQueue, type ImportItem } from "@/features/certificate-import";
import { PdfViewer } from "@/features/document-viewer";
import { useApiClient } from "@/lib/api";
import { es } from "@/lib/i18n";

export interface DocumentsPageProps {
  items: readonly ImportItem[];
  selectedDocumentId: number | null;
  onAddFiles(files: readonly File[]): void;
  onClearFinished(): void;
  onReview(certificateId: number, documentId?: number | null): void;
}

export function DocumentsPage({
  items,
  selectedDocumentId,
  onAddFiles,
  onClearFinished,
  onReview,
}: DocumentsPageProps) {
  const api = useApiClient();
  const fileUrl = selectedDocumentId
    ? api.url(`/api/v1/documents/${selectedDocumentId}/file`)
    : null;

  return (
    <div className="flex-1 flex overflow-hidden min-h-0 w-full">
      {/* Left Column: PDF Viewer */}
      <section
        className="w-[48%] bg-viewer-bg flex flex-col border-r border-slate-300 shrink-0 min-h-0"
        aria-label={es.viewer.title}
      >
        <PdfViewer fileUrl={fileUrl} />
      </section>

      {/* Right Column: Ingestion & Import Queue */}
      <main className="flex-1 bg-white flex flex-col min-w-0 overflow-y-auto p-6 gap-6">
        <header className="flex flex-col gap-1">
          <h2 className="text-lg font-bold text-slate-900">
            {es.certificateImport.title}
          </h2>
          <p className="text-xs text-slate-500">
            {es.certificateImport.description}
          </p>
        </header>

        <CertificateDropzone onFilesSelected={onAddFiles} />

        <ImportQueue
          items={items}
          onClearFinished={onClearFinished}
          onReview={onReview}
        />
      </main>
    </div>
  );
}
