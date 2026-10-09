import { FileText, History } from "lucide-react";
import { useMemo, useState } from "react";

import { AppShell, type BreadcrumbItem, type NavItem } from "@/components/layout";
import { ProcessingNotice, useCertificateImport } from "@/features/certificate-import";
import { ConnectionGate } from "@/features/connection-status";
import type { ApiClient } from "@/lib/api";
import { es } from "@/lib/i18n";
import { DocumentsPage, HistoryPage, ValidationPage } from "@/pages";

import { AppProviders } from "./providers/AppProviders";

export interface AppProps {
  apiClient?: ApiClient;
}

const NAV_ITEMS: readonly NavItem[] = [
  { id: "documents", label: es.nav.documents, icon: FileText },
  { id: "history", label: es.nav.history, icon: History },
];

function AppContent() {
  const [currentNav, setCurrentNav] = useState<"documents" | "history">("documents");
  const [selectedCertificateId, setSelectedCertificateId] = useState<number | null>(null);
  const [selectedDocumentId, setSelectedDocumentId] = useState<number | null>(null);
  const [deleted, setDeleted] = useState(false);

  const { items, addFiles, clearFinished, removeCertificate } = useCertificateImport();

  const handleReview = (certificateId: number, documentId?: number | null) => {
    setDeleted(false);
    setSelectedCertificateId(certificateId);
    setSelectedDocumentId(documentId ?? null);

  };

  const backToList = () => { setSelectedCertificateId(null); setSelectedDocumentId(null); };
  const breadcrumbs: readonly BreadcrumbItem[] = useMemo(() => selectedCertificateId === null
    ? [{ label: currentNav === "documents" ? es.nav.documents : es.nav.history }]
    : [{ label: currentNav === "documents" ? es.nav.documents : es.nav.history,
         onClick: () => { setSelectedCertificateId(null); setSelectedDocumentId(null); } },
       { label: `${es.header.millCertificate} #${selectedCertificateId}` }], [currentNav, selectedCertificateId]);

  return (
    <AppShell
      items={NAV_ITEMS}
      activeId={currentNav}
      onNavigate={(id) => {
        if (id === "documents" || id === "history") {
          setCurrentNav(id);
          setDeleted(false);
          backToList();
        }
      }}
      breadcrumbs={breadcrumbs}
    >
      <ConnectionGate>
        <div className="flex min-w-0 flex-1 flex-col">
        <ProcessingNotice items={items} />
        {deleted && <p role="status" className="px-6 py-3 text-sm">{es.certificateDeletion.success}</p>}
        {selectedCertificateId !== null ? (
          <ValidationPage key={`${selectedCertificateId}:${items.find((item) => item.certificateId === selectedCertificateId)?.phase ?? "saved"}`} certificateId={selectedCertificateId} documentId={selectedDocumentId} onBack={backToList}
            onDeleted={() => { removeCertificate(selectedCertificateId); setDeleted(true); backToList(); }} />
        ) : currentNav === "documents" ? (
          <DocumentsPage
            items={items}
            onAddFiles={addFiles}
            onClearFinished={clearFinished}
            onReview={handleReview}
          />
        ) : (
          <HistoryPage onReview={handleReview} />
        )}
        </div>
      </ConnectionGate>

    </AppShell>
  );
}

export function App({ apiClient }: AppProps) {
  return (
    <AppProviders {...(apiClient ? { apiClient } : {})}>
      <AppContent />
    </AppProviders>
  );
}
