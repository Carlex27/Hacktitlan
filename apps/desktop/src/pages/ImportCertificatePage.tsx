import { useState } from "react";

import { CertificateDropzone } from "../features/certificate-import";

export function ImportCertificatePage() {
  const [selectedFiles, setSelectedFiles] = useState<readonly File[]>([]);

  return (
    <section aria-labelledby="import-title">
      <h2 id="import-title">Importar actas de molino</h2>
      <p>Los certificados se procesan localmente.</p>
      <CertificateDropzone onFilesSelected={setSelectedFiles} />
      <p aria-live="polite">
        {selectedFiles.length === 0
          ? "No hay archivos seleccionados."
          : `${selectedFiles.length} archivo(s) seleccionado(s).`}
      </p>
    </section>
  );
}
