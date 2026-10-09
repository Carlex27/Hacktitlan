import { BookOpen, FileText, History } from "lucide-react";
import { useMemo, useState } from "react";

import { AppShell, type BreadcrumbItem, type NavItem } from "@/components/layout";
import { ProcessingNotice, useCertificateImport } from "@/features/certificate-import";
import { ConnectionGate } from "@/features/connection-status";
import { FormatLibrary } from "@/features/certificate-formats";
import type { ApiClient } from "@/lib/api";
import { es } from "@/lib/i18n";
import { ClassificationGuidePage, DocumentsPage, HistoryPage, ValidationPage } from "@/pages";

import { AppProviders } from "./providers/AppProviders";

export interface AppProps {
  apiClient?: ApiClient;
}

const NAV_ITEMS: readonly NavItem[] = [
  { id: "documents", label: es.nav.documents, icon: FileText },
  { id: "history", label: es.nav.history, icon: History },
  { id: "formats", label: es.formats.title, icon: FileText },
  { id: "guide", label: es.classificationGuide.title, icon: BookOpen },
];

function AppContent() {
  const [currentNav, setCurrentNav] = useState<"documents" | "history" | "formats" | "guide">("documents");
  const [selectedCertificateId, setSelectedCertificateId] = useState<number | null>(null);
  const [selectedDocumentId, setSelectedDocumentId] = useState<number | null>(null);
  const [deleted, setDeleted] = useState(false);
  const [sourceFileName, setSourceFileName] = useState<string | null>(null);

  const { items, addFiles, clearFinished, removeCertificate } = useCertificateImport();

  const handleReview = (certificateId: number, documentId?: number | null) => {
    setDeleted(false);
    setSourceFileName(null);
    setSelectedCertificateId(certificateId);
    setSelectedDocumentId(documentId ?? null);

  };

  const backToList = () => { setSelectedCertificateId(null); setSelectedDocumentId(null); };
  const breadcrumbs: readonly BreadcrumbItem[] = useMemo(() => selectedCertificateId === null
    ? [{ label: currentNav === "documents" ? es.nav.documents : currentNav === "formats" ? es.formats.title : currentNav === "guide" ? es.classificationGuide.title : es.nav.history }]
    : [{ label: currentNav === "documents" ? es.nav.documents : currentNav === "formats" ? es.formats.title : currentNav === "guide" ? es.classificationGuide.title : es.nav.history,
         onClick: () => { setSelectedCertificateId(null); setSelectedDocumentId(null); } },
       { label: sourceFileName?.toLowerCase().endsWith(".xlsx") ? sourceFileName : `${es.header.millCertificate} #${selectedCertificateId}` }], [currentNav, selectedCertificateId, sourceFileName]);

  return (
    <AppShell
      items={NAV_ITEMS}
      activeId={currentNav}
      onNavigate={(id) => {
        if (id === "documents" || id === "history" || id === "formats" || id === "guide") {
          setCurrentNav(id);
          setDeleted(false);
          backToList();
        }
      }}
      breadcrumbs={breadcrumbs}
    >
      {currentNav === "guide" ? <ClassificationGuidePage /> : <ConnectionGate>
        <div className="flex min-w-0 flex-1 flex-col">
        <ProcessingNotice items={items} />
        {deleted && <p role="status" className="px-6 py-3 text-sm">{es.certificateDeletion.success}</p>}
        {selectedCertificateId !== null ? (
          <ValidationPage key={`${selectedCertificateId}:${items.find((item) => item.certificateId === selectedCertificateId)?.phase ?? "saved"}`} certificateId={selectedCertificateId} documentId={selectedDocumentId} onBack={backToList}
            onSourceFileName={setSourceFileName}
            onOpenRevision={handleReview}
            onDeleted={() => { removeCertificate(selectedCertificateId); setDeleted(true); backToList(); }} />
        ) : currentNav === "documents" ? (
          <DocumentsPage
            items={items}
            onAddFiles={addFiles}
            onClearFinished={clearFinished}
            onReview={handleReview}
          />
        ) : currentNav === "formats" ? <FormatLibrary onOpenRevision={handleReview} /> : (
          <HistoryPage onReview={handleReview} />
        )}
        </div>
      </ConnectionGate>}

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
