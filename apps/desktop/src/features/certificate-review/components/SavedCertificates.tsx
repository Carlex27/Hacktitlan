import { LoadErrorAlert } from "@/components/feedback";
import { FileSearch, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Empty, EmptyHeader, EmptyTitle, EmptyDescription, EmptyMedia } from "@/components/ui/empty";
import { Spinner } from "@/components/ui/spinner";
import { CertificateFiltersForm } from "./CertificateFiltersForm";
import { SavedCertificateItem } from "./SavedCertificateItem";
import { es } from "@/lib/i18n";
import { useSavedCertificates } from "../hooks/useSavedCertificates";

export interface SavedCertificatesProps {
  refreshKey: string;
  onReview(certificateId: number, documentId: number): void;
}

export function SavedCertificates({ refreshKey, onReview }: SavedCertificatesProps) {
  const { state, loading, reload, nextPage, applyFilters, hasFilters } = useSavedCertificates(refreshKey);
  const text = es.savedCertificates;
  return <section className="space-y-6">
      <CertificateFiltersForm onApply={applyFilters} />
      <section aria-labelledby="saved-certificates-title" className="space-y-2">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h3 id="saved-certificates-title" className="text-lg leading-7 font-semibold">{text.title}</h3>
        <Button className="min-h-10" variant="outline" onClick={reload} disabled={loading}>
          <RefreshCw aria-hidden="true" />{text.refresh}
        </Button>
      </div>
      {loading ? <div role="status" className="flex min-h-40 items-center justify-center gap-3 text-sm text-muted-foreground">
        <Spinner aria-hidden="true" role="presentation" aria-label={undefined} />{text.loading}
      </div> : state?.error ?
        <LoadErrorAlert title={text.error} error={state.error} onRetry={reload} /> :
        state?.items.length === 0 ? <Empty className="min-h-48">
          <EmptyHeader><EmptyMedia variant="icon"><FileSearch aria-hidden="true" /></EmptyMedia>
            <EmptyTitle>{hasFilters ? es.workspace.noMatches : text.empty}</EmptyTitle>
            <EmptyDescription>{hasFilters ? text.noMatchesHint : text.emptyHint}</EmptyDescription>
          </EmptyHeader>
        </Empty> :
        <ul aria-label={text.title} className="divide-y divide-border">
          {state?.items.map((item) => <SavedCertificateItem key={item.id}
            number={item.certificate_no ?? text.unnamed(item.id)} manufacturer={item.manufacturer}
            date={item.certificate_date} status={item.approval_status}
            onReview={() => onReview(item.id, item.document_id)} />)}
        </ul>}
      {!loading && state?.nextCursor && <div className="border-t border-border pt-4"><Button variant="outline" className="min-h-10" onClick={nextPage}>{text.more}</Button></div>}
      </section>
  </section>;
}
