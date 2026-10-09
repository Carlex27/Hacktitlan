import { ArrowLeft, FileText, RotateCw } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { DeleteCertificateButton, HeatReview, useCertificate } from "@/features/certificate-review";
import {
  ApprovalBar,
  ReclassificationForm,
  ClassificationValidationTab,
  EvidenceArea,
  useClassificationRun,
  useEvidence,
} from "@/features/classification-results";
import { PdfViewer } from "@/features/document-viewer";
import { FormatLibrary } from "@/features/certificate-formats";
import {
  TariffReferenceButton,
  TariffReferenceViewer,
  useTariffReference,
} from "@/features/tariff-reference";
import type { SourceReference } from "@/features/classification-results";
import { es } from "@/lib/i18n";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export interface ValidationPageProps {
  certificateId: number | null;
  documentId: number | null;
  onBack?: () => void;
  onDeleted?: () => void;
  onSourceFileName?: (name: string | null) => void;
  onOpenRevision?: (certificateId: number, documentId?: number | null) => void;
}

export function ValidationPage({ certificateId, documentId, onBack, onDeleted, onSourceFileName, onOpenRevision }: ValidationPageProps) {
  const [formatOpen, setFormatOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<"rolls" | "extracted" | "validation" | "approval">("rolls");
  const [selectedHeatId, setSelectedHeatId] = useState<number | null | undefined>(undefined);
  const [pdfPage, setPdfPage] = useState(1);
  const [viewerOpen, setViewerOpen] = useState(false);
  const reviewMain = useRef<HTMLElement>(null);
  const reviewContent = useRef<HTMLDivElement>(null);

  const {
    certificate,
    isLoading: certLoading,
    error: certError,
    reload: reloadCertificate,
  } = useCertificate(certificateId);
  useEffect(() => {
    onSourceFileName?.(certificate?.source_file_name ?? null);
  }, [certificate?.source_file_name, onSourceFileName]);
  const {
    run,
    isLoading: runLoading,
    error: runError,
    reload: reloadRun,
  } = useClassificationRun(certificateId);
  const evidence = useEvidence();
  const tariffReference = useTariffReference();
  const [viewerTab, setViewerTab] = useState<"acta" | "ligie">("acta");

  const openTariffReference = (reference: SourceReference, label: string) => {
    tariffReference.open(reference, label);
    setViewerTab("ligie");
    setViewerOpen(true);
  };
  const goToActaPage = (page: number) => {
    setPdfPage(page);
    setViewerTab("acta");
    setViewerOpen(true);
  };

  const docId = documentId ?? certificate?.document_id ?? null;
  const filePath = docId ? `/api/v1/documents/${docId}/file` : null;
  const refreshButton = <Button type="button" variant="outline" onClick={reloadRun} className="min-h-11" title={es.tabs.reExtract}>
    <RotateCw aria-hidden="true" className="size-4" />
    <span>{es.tabs.reExtract}</span>
  </Button>;

  if (formatOpen) return <FormatLibrary documentId={docId} certificateId={certificateId} onBack={() => setFormatOpen(false)} {...(onOpenRevision ? { onOpenRevision } : {})} />;
  return (
    <div className="flex-1 flex overflow-hidden min-h-0 w-full">
      <main ref={reviewMain} className="flex-1 bg-background text-foreground text-sm leading-5 flex flex-col min-w-0 overflow-y-auto overscroll-y-contain lg:overflow-hidden min-h-0">
        <div className="shrink-0 border-b border-border px-4 py-3 sm:px-8">
          <div className="mx-auto flex w-full max-w-6xl flex-wrap items-center justify-between gap-3">
          <div>{onBack && <Button className="min-h-11" variant="ghost" onClick={onBack}><ArrowLeft aria-hidden="true" />{es.workspace.back}</Button>}</div>
          <div className="flex flex-wrap gap-2"><Button className="min-h-11" variant="outline" disabled={!docId || certificate?.source_file_name?.toLowerCase().endsWith(".xlsx")} onClick={() => setFormatOpen(true)}>{es.formats.configure}</Button>
          <Button className="min-h-11" variant="outline" onClick={() => { if (viewerOpen) setViewerOpen(false); else { setViewerTab("acta"); setViewerOpen(true); } }} disabled={!docId}>
            <FileText aria-hidden="true" />{viewerOpen ? es.workspace.closeViewer : es.workspace.original}
          </Button></div>
          </div>
        </div>
        <header className="px-4 sm:px-8 py-3 border-b border-border shrink-0 bg-background">
          <div className="mx-auto flex w-full max-w-6xl flex-wrap items-center justify-between gap-3">
          <nav aria-label={es.workspace.reviewSections} className="grid w-full min-w-0 grid-cols-2 gap-1 rounded-xl bg-muted p-1 sm:flex sm:w-auto sm:flex-wrap">
            {(["rolls", "extracted", "validation", "approval"] as const).map((tab) => (
              <Button key={tab} type="button" variant="ghost" onClick={() => {
                if (reviewMain.current) reviewMain.current.scrollTop = 0;
                if (reviewContent.current) reviewContent.current.scrollTop = 0;
                setActiveTab(tab);
              }} aria-current={activeTab === tab ? "true" : undefined}
                className={cn("min-h-11 whitespace-normal px-3 text-center", activeTab === tab ? "bg-background text-foreground shadow-sm hover:bg-background" : "text-muted-foreground hover:text-foreground")}>
                {tab === "rolls" ? es.workspace.reviewTitle : es.tabs[tab]}
              </Button>
            ))}
          </nav>
          {certificateId !== null
            ? <ReclassificationForm key={certificateId} certificateId={certificateId} onComplete={reloadRun}>
                {onDeleted && <DeleteCertificateButton key={certificateId} certificateId={certificateId} onDeleted={onDeleted} />}
                {refreshButton}
              </ReclassificationForm>
            : refreshButton}
          </div>
        </header>

        <div className="shrink-0 lg:flex-1 flex flex-col lg:flex-row lg:min-h-0 lg:overflow-hidden">
        <div ref={reviewContent} className="lg:flex-1 lg:overflow-y-auto overscroll-y-contain px-4 py-8 sm:px-8 space-y-8 [&>*]:w-full [&>*]:max-w-6xl [&>*]:mx-auto bg-muted/20 lg:min-h-0 min-w-0">
          <EvidenceArea state={evidence.state} onRetry={evidence.retry} onClose={evidence.close} onGoToPage={goToActaPage} onOpenSource={openTariffReference} />
          {(activeTab === "rolls" || activeTab === "extracted") && <HeatReview certificate={certificate} isLoading={certLoading}
            error={certError} onRetry={reloadCertificate} selectedHeatId={selectedHeatId} onSelectHeat={setSelectedHeatId}
            onShowExtracted={() => setActiveTab("extracted")} detailed={activeTab === "extracted"} classificationResults={run?.results ?? []} classificationLoading={runLoading}
            classificationError={runError} onRetryClassification={reloadRun} />}
          {activeTab === "validation" && <ClassificationValidationTab products={certificate?.products ?? []} run={run} isLoading={runLoading} error={runError} onViewEvidence={evidence.open} onReloadRun={reloadRun}
            renderTariffAction={(reference, displayCode) => (
              <TariffReferenceButton reference={reference} displayCode={displayCode} onOpen={openTariffReference} />
            )} />}
          <div hidden={activeTab !== "approval"}>
            <ApprovalBar run={run} certificate={certificate} isLoading={certLoading || runLoading} loadError={certError || runError}
              onDecisionComplete={() => { reloadRun(); reloadCertificate(); }} />
          </div>
        </div>

          {viewerOpen && <aside className="relative h-[75vh] lg:h-auto lg:w-[46%] lg:min-w-80 shrink-0 flex flex-col min-h-0 border-t lg:border-t-0 lg:border-l border-border bg-background" aria-label={es.viewer.title}>
            {viewerTab === "acta"
              ? <PdfViewer filePath={filePath} page={pdfPage} fileName={certificate?.certificate_no ? `Acta ${certificate.certificate_no}` : null} />
              : <TariffReferenceViewer active={tariffReference.active} />}
          </aside>}
        </div>

      </main>
    </div>
  );
}
