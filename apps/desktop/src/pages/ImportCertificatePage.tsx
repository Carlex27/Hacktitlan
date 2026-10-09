import { CertificateImporter } from "../features/certificate-import";
import { useCertificateImport } from "@/features/certificate-import";

import { DocumentsPage } from "./DocumentsPage";

export interface ImportCertificatePageProps {
  apiBaseUrl?: string;
  selectedDocumentId?: number | null;
  onReview?: (certificateId: number, documentId?: number | null) => void;
}

/** Página de importación de certificados (vista inicial de documentos). */
export function ImportCertificatePage({
  apiBaseUrl,
  selectedDocumentId = null,
  onReview = () => {},
}: ImportCertificatePageProps) {
  const { items, addFiles, clearFinished } = useCertificateImport();

  if (apiBaseUrl) {
    return <CertificateImporter apiBaseUrl={apiBaseUrl} />;
  }

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
}
