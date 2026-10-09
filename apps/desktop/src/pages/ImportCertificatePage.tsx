import { CertificateImporter } from "../features/certificate-import";

export function ImportCertificatePage({ apiBaseUrl }: { apiBaseUrl: string }) {
  return <CertificateImporter apiBaseUrl={apiBaseUrl} />;
}
