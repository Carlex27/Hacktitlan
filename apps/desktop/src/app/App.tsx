import { AppShell } from "../components/layout/AppShell";
import { ImportCertificatePage } from "../pages/ImportCertificatePage";
import { DocumentReviewList } from "../features/certificate-review";

export function App({ apiBaseUrl = window.location.origin }: { apiBaseUrl?: string }) {
  return (
    <AppShell>
      <ImportCertificatePage />
      <DocumentReviewList apiBaseUrl={apiBaseUrl} />
    </AppShell>
  );
}
