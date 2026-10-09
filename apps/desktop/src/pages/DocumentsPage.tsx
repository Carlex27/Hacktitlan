import { CertificateDropzone, ImportQueue, completedImportKey, type ImportItem } from "@/features/certificate-import";
import { DocumentReviewQueue } from "@/features/document-review";
import { es } from "@/lib/i18n";

export interface DocumentsPageProps {
  items: readonly ImportItem[];
  onAddFiles(files: readonly File[]): void;
  onClearFinished(): void;
  onReview(certificateId: number, documentId?: number | null): void;
}

export function DocumentsPage({
  items,
  onAddFiles,
  onClearFinished,
  onReview,
}: DocumentsPageProps) {
  return (
    <div className="flex-1 flex overflow-hidden min-h-0 w-full">
      {/* `*:shrink-0`: las tarjetas (overflow-hidden) no deben comprimirse para caber;
          la columna crece y se recorre con scroll. */}
      <main className="flex-1 bg-background flex flex-col min-w-0 min-h-0 overflow-y-auto [scrollbar-gutter:stable] px-4 py-8 sm:px-8 gap-8 *:shrink-0 [&>*]:w-full [&>*]:max-w-6xl [&>*]:mx-auto">
        <header className="flex flex-col gap-1">
          <h2 className="text-2xl leading-8 font-semibold text-foreground">
            {es.certificateImport.title}
          </h2>
          <p className="text-base leading-6 text-muted-foreground max-w-prose">
            {es.certificateImport.description}
          </p>
        </header>

        <CertificateDropzone onFilesSelected={onAddFiles} />

        <ImportQueue
          items={items}
          onClearFinished={onClearFinished}
          onReview={onReview}
        />

        <p className="text-sm leading-5 text-muted-foreground">{es.workspace.processing}</p>
        <DocumentReviewQueue onReview={onReview} refreshKey={completedImportKey(items)} />
      </main>
    </div>
  );
}
