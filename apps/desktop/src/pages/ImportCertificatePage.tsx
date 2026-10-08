import { useCertificateImport } from "@/features/certificate-import";

import { DocumentsPage } from "./DocumentsPage";

export interface ImportCertificatePageProps {
  selectedDocumentId?: number | null;
  onReview?: (certificateId: number, documentId?: number | null) => void;
}

/** Página de importación de certificados (vista inicial de documentos). */
export function ImportCertificatePage({
  selectedDocumentId = null,
  onReview = () => {},
}: ImportCertificatePageProps) {
  const { items, addFiles, clearFinished } = useCertificateImport();

  return (
    <DocumentsPage
      items={items}
      selectedDocumentId={selectedDocumentId}
      onAddFiles={addFiles}
      onClearFinished={clearFinished}
      onReview={onReview}
    />
  );
}
