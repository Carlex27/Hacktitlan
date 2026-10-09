import { RotateCw } from "lucide-react";
import { useState } from "react";

import { CertificateReviewTab, useCertificate } from "@/features/certificate-review";
import {
  ApprovalBar,
  ClassificationValidationTab,
  EvidenceArea,
  RunSelectionHistory,
  useClassificationRun,
  useEvidence,
} from "@/features/classification-results";
import { PdfViewer } from "@/features/document-viewer";
import {
  SourceDocumentTabs,
  TariffReferenceButton,
  TariffReferenceViewer,
  useTariffReference,
  type SourceDocumentTab,
} from "@/features/tariff-reference";
import type { SourceReference } from "@/features/classification-results";
import { es } from "@/lib/i18n";
import { cn } from "@/lib/utils";

export interface ValidationPageProps {
  certificateId: number | null;
  documentId: number | null;
}

export function ValidationPage({ certificateId, documentId }: ValidationPageProps) {
  const [activeTab, setActiveTab] = useState<"extracted" | "validation" | "analysis" | "history">("extracted");
  const [pdfPage, setPdfPage] = useState(1);

  const {
    certificate,
    isLoading: certLoading,
    error: certError,
    reload: reloadCertificate,
  } = useCertificate(certificateId);
  const {
    run,
    isLoading: runLoading,
    error: runError,
    reload: reloadRun,
  } = useClassificationRun(certificateId);
  const evidence = useEvidence();
  const tariffReference = useTariffReference();
  const [viewerTab, setViewerTab] = useState<SourceDocumentTab>("acta");

  const openTariffReference = (reference: SourceReference, label: string) => {
    tariffReference.open(reference, label);
    setViewerTab("ligie");
  };
  const goToActaPage = (page: number) => {
    setPdfPage(page);
    setViewerTab("acta");
  };

  const docId = documentId ?? certificate?.document_id ?? null;
  const filePath = docId ? `/api/v1/documents/${docId}/file` : null;

  return (
    <div className="flex-1 flex overflow-hidden min-h-0 w-full">
      <section className="w-[48%] bg-viewer-bg flex flex-col border-r border-slate-300 shrink-0 min-h-0" aria-label={es.viewer.title}>
        <SourceDocumentTabs
          activeTab={viewerTab}
          onTabChange={setViewerTab}
          activeReference={tariffReference.active}
          actaViewer={<PdfViewer filePath={filePath} page={pdfPage} fileName={certificate?.certificate_no ? `Acta_${certificate.certificate_no}.pdf` : null} />}
          ligieViewer={<TariffReferenceViewer active={tariffReference.active} />}
        />
      </section>

      <main className="flex-1 bg-white flex flex-col min-w-0 overflow-hidden min-h-0">
        <header className="h-11 px-4 border-b border-slate-200 flex items-center justify-between gap-3 shrink-0 bg-white">
          <nav aria-label="Secciones de validación" className="flex min-w-0 gap-6 h-full overflow-x-auto text-xs font-semibold">
            {(["extracted", "validation", "analysis", "history"] as const).map((tab) => (
              <button key={tab} type="button" onClick={() => setActiveTab(tab)} aria-current={activeTab === tab ? "true" : undefined}
                className={cn("flex shrink-0 items-center h-full px-1 transition-colors select-none", activeTab === tab ? "text-blue-600 border-b-2 border-blue-600" : "text-slate-500 hover:text-slate-800")}>
                {es.tabs[tab]}
              </button>
            ))}
          </nav>
          <button type="button" onClick={reloadRun} className="inline-flex shrink-0 items-center gap-1.5 px-2.5 py-1 bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 text-xs font-medium rounded shadow-sm transition" title={es.tabs.reExtract}>
            <RotateCw aria-hidden="true" className="w-3.5 h-3.5 text-slate-500" />
            <span>{es.tabs.reExtract}</span>
          </button>
        </header>

        <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-slate-50/60 min-h-0">
          <EvidenceArea state={evidence.state} onRetry={evidence.retry} onClose={evidence.close} onGoToPage={goToActaPage} onOpenSource={openTariffReference} />
          {activeTab === "extracted" && <CertificateReviewTab certificate={certificate} isLoading={certLoading} error={certError} onRetry={reloadCertificate} />}
          {activeTab === "validation" && <ClassificationValidationTab run={run} isLoading={runLoading} error={runError} onViewEvidence={evidence.open} onReloadRun={reloadRun}
            renderTariffAction={(reference, displayCode) => (
              <TariffReferenceButton reference={reference} displayCode={displayCode} onOpen={openTariffReference} />
            )} />}
          {activeTab === "analysis" && (
            <div className="bg-white p-6 rounded-lg border border-slate-200 shadow-sm text-center text-slate-500 text-xs">
              {es.tabs.comingSoonDescription}
            </div>
          )}
          {activeTab === "history" && (
            <RunSelectionHistory run={run} isLoading={runLoading} error={runError} onRetry={reloadRun} />
          )}
        </div>

        <ApprovalBar run={run} onDecisionComplete={reloadRun} />
      </main>
    </div>
  );
}
