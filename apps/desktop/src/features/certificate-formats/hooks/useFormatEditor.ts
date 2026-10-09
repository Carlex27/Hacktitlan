import { useCallback, useEffect, useRef, useState } from "react";
import { applyFormat, confirmFormatTest, createFormat, describeApiError, getFormat, getFormatLayout, getJob,
  listFormats, listFormatTests, listCertificates, getPreparedLayout, newFormatVersion, prepareFormatLayout, runFormatTest, saveFormatVersion,
  transitionFormat, useApiClient, type ActorReasonDto, type CertificateSummaryDto, type FormatDetailDto, type FormatDto,
  type FormatTestDto, type FormatVersionDto, type LayoutDto, type TemplateConfigurationDto } from "@/lib/api";

export function useFormatEditor(initialDocumentId: number | null, initialCertificateId: number | null) {
  const api = useApiClient();
  const [formats, setFormats] = useState<FormatDto[]>([]);
  const [examples, setExamples] = useState<CertificateSummaryDto[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [offset, setOffset] = useState(0);
  const [detail, setDetail] = useState<FormatDetailDto | null>(null);
  const [version, setVersion] = useState<FormatVersionDto | null>(null);
  const [configuration, setConfiguration] = useState<TemplateConfigurationDto | null>(null);
  const [documentId, setDocumentId] = useState(initialDocumentId);
  const [certificateId, setCertificateId] = useState(initialCertificateId);
  const [layout, setLayout] = useState<LayoutDto | null>(null);
  const [tests, setTests] = useState<FormatTestDto[]>([]);
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState<"loading" | "empty" | "success" | "needs_review" | "error">("loading");
  const [error, setError] = useState<string | null>(null);
  const [jobId, setJobId] = useState<number | null>(null);
  const [progress, setProgress] = useState<number | null>(null);
  const [applied, setApplied] = useState<{ certificate_id: number; job_id: number } | null>(null);
  const abort = useRef(new AbortController());
  const locked = useRef(false);
  const formatQuery = useRef("");
  const dirty = !!version && !!configuration && JSON.stringify(configuration) !== JSON.stringify(version.configuration);

  const perform = useCallback(async (operation: () => Promise<void> | Promise<"success" | "empty" | "needs_review" | undefined>) => {
    if (locked.current) return;
    locked.current = true; setBusy(true); setError(null); setStatus("loading");
    const controller = abort.current;
    try { const outcome = await operation(); if (!controller.signal.aborted) setStatus(outcome ?? "success"); }
    catch (cause) { if (!controller.signal.aborted) { setError(cause instanceof Error && !("kind" in cause) ? cause.message : describeApiError(cause)); setStatus("error"); } }
    finally { locked.current = false; if (!controller.signal.aborted) setBusy(false); }
  }, []);

  const loadLibrary = useCallback(async (signal: AbortSignal) => {
    const [rows, certificates] = await Promise.all([listFormats(api, 0, { signal }, formatQuery.current), listCertificates(api, null, { signal })]);
    if (signal.aborted) return;
    setFormats(rows); setOffset(0); setExamples([...certificates.data]);
    setCursor(typeof certificates.meta.next_cursor === "string" ? certificates.meta.next_cursor : null);
  }, [api]);
  const reload = useCallback(() => perform(() => loadLibrary(abort.current.signal)), [perform, loadLibrary]);
  useEffect(() => {
    const controller = new AbortController();
    abort.current = controller;
    void Promise.resolve().then(() => loadLibrary(controller.signal)).then(() => { if (!controller.signal.aborted) setStatus("success"); })
      .catch(cause => { if (!controller.signal.aborted) { setError(describeApiError(cause)); setStatus("error"); } });
    return () => controller.abort();
  }, [loadLibrary]);

  const loadVersion = async (next: FormatVersionDto) => {
    const rows = await listFormatTests(api, next.id, { signal: abort.current.signal });
    if (abort.current.signal.aborted) return;
    setVersion(next); setConfiguration(next.configuration); setTests(rows);
  };
  const open = (id: number) => perform(async () => {
    const next = await getFormat(api, id, { signal: abort.current.signal });
    const latest = next.versions.at(-1);
    if (latest) await loadVersion(latest);
    setDetail(next);
  });
  const save = async (actor: ActorReasonDto) => {
    if (!version || !configuration) return null;
    const saved = dirty ? await saveFormatVersion(api, version, configuration, actor) : version;
    setVersion(saved); setConfiguration(saved.configuration);
    setDetail(previous => previous ? { ...previous, versions: previous.versions.map(v => v.id === saved.id ? saved : v) } : previous);
    setTests(await listFormatTests(api, saved.id));
    return saved;
  };
  const waitJob = async (id: number) => {
    setJobId(id); setProgress(null);
    try {
      while (!abort.current.signal.aborted) {
        const job = await getJob(api, id, { signal: abort.current.signal });
        setProgress(job.progress);
        if (job.status === "failed" || job.status === "cancelled") throw new Error(job.error_message ?? job.status);
        if (!["queued", "running"].includes(job.status)) return job.status;
        await new Promise(resolve => setTimeout(resolve, 1000));
      }
      throw new Error("Solicitud cancelada");
    } finally { setJobId(null); }
  };
  return { formats, examples, cursor, offset, detail, version, configuration, setConfiguration, documentId, certificateId,
    layout, tests, busy, status: status === "success" && !formats.length ? "empty" : status, error, dirty, jobId, progress, applied,
    reload, open,
    selectVersion: (id: number) => { const next = detail?.versions.find(v => v.id === id); if (next) void perform(() => loadVersion(next)); },
    selectExample: (doc: number, cert: number) => { setDocumentId(doc); setCertificateId(cert); setLayout(null); setApplied(null); },
    search: (query: string) => perform(async () => { formatQuery.current = query.trim(); setFormats(await listFormats(api, 0, undefined, formatQuery.current)); setOffset(0); }),
    moreFormats: () => perform(async () => { const next = offset + 50; setFormats(await listFormats(api, next, undefined, formatQuery.current)); setOffset(next); }),
    moreExamples: () => perform(async () => { if (!cursor) return; const next = await listCertificates(api, cursor);
      setExamples(previous => [...previous, ...next.data]); setCursor(typeof next.meta.next_cursor === "string" ? next.meta.next_cursor : null); }),
    create: (name: string, actor: ActorReasonDto) => perform(async () => {
      const created = await createFormat(api, name, actor); const next = await getFormat(api, created.id);
      const latest = next.versions.at(-1); if (latest) await loadVersion(latest);
      setDetail(next); setFormats(previous => [...previous, created]);
    }),
    save: (actor: ActorReasonDto) => perform(async () => { await save(actor); }),
    prepare: (actor: ActorReasonDto) => perform(async () => {
      if (!documentId) return;
      const job = await prepareFormatLayout(api, documentId, actor); const outcome = await waitJob(job.job_id);
      if (!abort.current.signal.aborted) setLayout(await getFormatLayout(api, documentId));
      return outcome === "needs_ocr" ? "needs_review" : "success";
    }),
    test: (actor: ActorReasonDto) => perform(async () => {
      if (!layout) return; const saved = await save(actor); if (!saved) return;
      const created = await runFormatTest(api, saved, layout.id, actor);
      if (created.job_id) await waitJob(created.job_id);
      const completed = await listFormatTests(api, saved.id);
      setTests(completed);
      const result = completed.find(test => test.id === created.id)?.result;
      return result?.status === "empty" ? "empty" : result?.status === "success" ? "success" : "needs_review";
    }),
    confirm: (id: number, actor: ActorReasonDto) => perform(async () => {
      const reviewed = await confirmFormatTest(api, id, actor); setTests(previous => previous.map(t => t.id === id ? reviewed : t));
    }),
    inspectTest: (test: FormatTestDto) => perform(async () => {
      const prepared = await getPreparedLayout(api, test.layout_id);
      setLayout(prepared); setDocumentId(test.document_id);
      setCertificateId(examples.find(item => item.document_id === test.document_id)?.id ?? null);
    }),
    transition: (action: "activate" | "retire", actor: ActorReasonDto) => perform(async () => {
      if (!version) return; const next = await transitionFormat(api, version, action, actor);
      await loadVersion(next); setDetail(await getFormat(api, next.format_id));
    }),
    newVersion: (actor: ActorReasonDto) => perform(async () => {
      if (!version) return; const next = await newFormatVersion(api, version, actor);
      await loadVersion(next); setDetail(await getFormat(api, next.format_id));
    }),
    apply: (actor: ActorReasonDto) => perform(async () => {
      if (!certificateId || !version) return;
      const created = await applyFormat(api, certificateId, version.id, actor);
      await waitJob(created.job_id); setApplied(created);
    }),
    cancel: (actor: ActorReasonDto) => { if (jobId) void api.post(`/api/v1/jobs/${jobId}/cancel`, actor).catch(cause => setError(describeApiError(cause))); },
  };
}
export type FormatEditorController = ReturnType<typeof useFormatEditor>;
