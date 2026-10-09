import { BarChart3, FileText, History, Settings, ShieldCheck } from "lucide-react";
import { useMemo, useState } from "react";

import { AppShell, type BreadcrumbItem, type NavItem } from "@/components/layout";
import { useCertificateImport } from "@/features/certificate-import";
import { ConnectionGate } from "@/features/connection-status";
import type { ApiClient } from "@/lib/api";
import { es } from "@/lib/i18n";
import { DocumentsPage, ValidationPage } from "@/pages";

import { AppProviders } from "./providers/AppProviders";

export interface AppProps {
  apiClient?: ApiClient;
}

const NAV_ITEMS: readonly NavItem[] = [
  { id: "documents", label: es.nav.documents, icon: FileText },
  { id: "validation", label: es.nav.validation, icon: ShieldCheck },
  { id: "history", label: es.nav.history, icon: History, disabled: true },
  { id: "reports", label: es.nav.reports, icon: BarChart3, disabled: true },
  { id: "settings", label: es.nav.settings, icon: Settings, disabled: true },
];

function AppContent() {
  const [currentNav, setCurrentNav] = useState<"documents" | "validation">("documents");
  const [selectedCertificateId, setSelectedCertificateId] = useState<number | null>(null);
  const [selectedDocumentId, setSelectedDocumentId] = useState<number | null>(null);

  const { items, addFiles, clearFinished } = useCertificateImport();

  const handleReview = (certificateId: number, documentId?: number | null) => {
    setSelectedCertificateId(certificateId);
    setSelectedDocumentId(documentId ?? null);
    setCurrentNav("validation");
  };

  const breadcrumbs: readonly BreadcrumbItem[] = useMemo(() => {
    if (currentNav === "documents") {
      return [{ label: es.nav.documents }];
    }

    const backToDocs = () => setCurrentNav("documents");
    if (selectedCertificateId !== null) {
      return [
        { label: es.nav.documents, onClick: backToDocs },
        { label: `${es.header.millCertificate} #${selectedCertificateId}` },
      ];
    }

    return [
      { label: es.nav.documents, onClick: backToDocs },
      { label: es.nav.validation },
    ];
  }, [currentNav, selectedCertificateId]);

  return (
    <AppShell
      items={NAV_ITEMS}
      activeId={currentNav}
      onNavigate={(id) => {
        if (id === "documents" || id === "validation") {
          setCurrentNav(id);
        }
      }}
      breadcrumbs={breadcrumbs}
    >
      <ConnectionGate>
        {currentNav === "documents" ? (
          <DocumentsPage
            items={items}
            selectedDocumentId={selectedDocumentId}
            onAddFiles={addFiles}
            onClearFinished={clearFinished}
            onReview={handleReview}
          />
        ) : (
          <ValidationPage
            certificateId={selectedCertificateId}
            documentId={selectedDocumentId}
          />
        )}
      </ConnectionGate>

      <ImportCertificatePage apiBaseUrl={apiBaseUrl} />
      <DocumentReviewList apiBaseUrl={apiBaseUrl} />
    </AppShell>
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
