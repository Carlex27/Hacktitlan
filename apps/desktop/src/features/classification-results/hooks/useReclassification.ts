import { useEffect, useState } from "react";
import { getJob, reclassifyCertificate, useApiClient, type JobDto } from "@/lib/api";

export function useReclassification(certificateId: number, onComplete: () => void) {
  const api = useApiClient();
  const [jobId, setJobId] = useState<number | null>(null);
  const [job, setJob] = useState<JobDto | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [version, setVersion] = useState(0);
  useEffect(() => {
    if (jobId === null) return;
    const activeJobId = jobId;
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout> | undefined;
    async function poll() {
      try {
        const next = await getJob(api, activeJobId, { signal: controller.signal });
        if (controller.signal.aborted) return;
        setJob(next);
        if (next.status === "queued" || next.status === "running") timer = setTimeout(poll, 1500);
        else onComplete();
      } catch (cause) { if (!controller.signal.aborted) setError(cause); }
    }
    void poll();
    return () => { controller.abort(); clearTimeout(timer); };
  }, [api, jobId, version, onComplete]);
  async function start(personName: string, reason: string) {
    setSubmitting(true);
    setError(null);
    try {
      const result = await reclassifyCertificate(api, certificateId, { person_name: personName, reason });
      setJob(null);
      setJobId(result.job_id);
      setVersion((value) => value + 1);
      return true;
    } catch (cause) { setError(cause); return false; }
    finally { setSubmitting(false); }
  }
  return { job, jobId, submitting, error, start,
    retry: () => { setError(null); setVersion((value) => value + 1); },
    processing: jobId !== null && (job === null || job.status === "queued" || job.status === "running"),
  };
}
