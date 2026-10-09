import { CertificateDropzone } from "./CertificateDropzone";
import { importTexts } from "../texts";
import { useCertificateImport } from "../useCertificateImport";

export function CertificateImporter({ apiBaseUrl }: { apiBaseUrl: string }) {
  const { files, receipts, status, error, uploading, selectFiles, submit, retryTracking } = useCertificateImport(apiBaseUrl);
  const loading = status === "loading";
  return (
    <section aria-labelledby="import-title" aria-busy={loading}>
      <h2 id="import-title">{importTexts.title}</h2>
      <p>{importTexts.description}</p>
      <CertificateDropzone disabled={loading} {...(error ? { errorId: "import-error" } : {})} onFilesSelected={selectFiles} />
      <p aria-live="polite">
        {files.length ? importTexts.selected(files.length) : importTexts.empty}
      </p>
      <button disabled={loading || files.length === 0} onClick={() => void submit()}>
        {uploading ? importTexts.uploading : loading ? importTexts.processing : importTexts.submit}
      </button>
      {uploading && <progress aria-label={importTexts.uploading} />}
      {error && <p id="import-error" role="alert">{error}</p>}
      {status === "success" && <p role="status">{importTexts.received}</p>}
      {status === "needs_review" && <p role="status">{importTexts.pendingReview}</p>}
      <ul>
        {receipts.map(({ name, receipt, job, trackingError }) => (
          <li key={`${name}-${receipt.document_id}`}>
            <p>{name}: {receipt.duplicate ? importTexts.duplicate : importTexts.queued}</p>
            {receipt.job_id !== null && <>
              {!trackingError && <progress max={100} value={job?.progress} aria-label={importTexts.progress(name)} />}
              <p role="status">
                {trackingError ? importTexts.trackingError : job ?
                  `${job.status === "running" && job.progress >= 95 ? importTexts.saving : importTexts.jobStatus[job.status]} (${job.progress} %)` : importTexts.queued}
              </p>
              {job && job.attempts > 1 && <p>{importTexts.retryAttempt(job.attempts)}</p>}
              {job?.error_message && job.status === "failed" && <p role="alert">{job.error_message}</p>}
              {trackingError && <>
                <p role="alert">{trackingError}</p>
                <button onClick={() => retryTracking(receipt.document_id)}>{importTexts.retryTracking}</button>
              </>}
            </>}
          </li>
        ))}
      </ul>
    </section>
  );
}
