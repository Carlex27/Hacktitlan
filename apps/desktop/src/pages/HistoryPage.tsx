import { SavedCertificates } from "@/features/certificate-review";
import { es } from "@/lib/i18n";

export function HistoryPage({ onReview }: { onReview(certificateId: number, documentId: number): void }) {
  return <main className="flex-1 flex flex-col min-w-0 min-h-0 overflow-y-auto bg-background px-4 py-8 sm:px-8 gap-8 *:shrink-0 [&>*]:w-full [&>*]:max-w-6xl [&>*]:mx-auto text-foreground">
    <header className="flex flex-col gap-1"><h2 className="text-2xl leading-8 font-semibold">{es.nav.history}</h2>
      <p className="max-w-prose text-base leading-6 text-muted-foreground">{es.workspace.historyDescription}</p></header>
    <SavedCertificates refreshKey="history" onReview={onReview} />
  </main>;
}
