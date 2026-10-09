import { SavedCertificates } from "@/features/certificate-review";
import { es } from "@/lib/i18n";

export function HistoryPage({ onReview }: { onReview(certificateId: number, documentId: number): void }) {
  return <main className="flex-1 min-w-0 overflow-y-auto bg-background p-4 sm:p-6 space-y-6 text-foreground">
    <header><h2 className="text-2xl leading-8 font-semibold">{es.nav.history}</h2>
      <p className="mt-2 max-w-prose text-base leading-6 text-muted-foreground">{es.workspace.historyDescription}</p></header>
    <SavedCertificates refreshKey="history" onReview={onReview} />
  </main>;
}
