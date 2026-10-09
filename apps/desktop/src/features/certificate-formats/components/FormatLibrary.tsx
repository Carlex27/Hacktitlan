import { useId, useState } from "react";
import { SelectField } from "@/components/ui";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { FormatVersionToolbar } from "./FormatVersionToolbar";
import { Progress } from "@/components/ui/progress";
import type { RegionDto } from "@/lib/api";
import { es } from "@/lib/i18n";
import { useFormatEditor } from "../hooks/useFormatEditor";
import { PageRegionSurface } from "./PageRegionSurface";
import { MappingPanel } from "./MappingPanel";
import { FormatTestResults } from "./FormatTestResults";

export interface FormatLibraryProps {
  documentId?: number | null; certificateId?: number | null;
  onBack?: () => void; onOpenRevision?: (certificateId: number, documentId?: number | null) => void;
}
const actor = { person_name: "Administrador", reason: "Configuración de formatos desde la biblioteca web" };
export function FormatLibrary({ documentId = null, certificateId = null, onBack, onOpenRevision }: FormatLibraryProps) {
  const selectId = useId();
  const exampleId = useId();
  const editor = useFormatEditor(documentId, certificateId);
  const [name, setName] = useState("");
  const [query, setQuery] = useState("");
  const [pageNumber, setPageNumber] = useState(1);
  const [region, setRegion] = useState<RegionDto | null>(null);
  const [zoom, setZoom] = useState(100);
  const blocked = editor.busy || editor.status === "loading";
  const page = editor.layout?.document.pages.find(p => p.page_number === pageNumber) ?? editor.layout?.document.pages[0] ?? null;
  const { version, configuration } = editor;
  return <div className="w-full min-h-0 flex-1 overflow-y-auto bg-background text-foreground"><div className="mx-auto max-w-[100rem] px-4 py-8 sm:px-8 space-y-6">
    <header className="flex flex-wrap items-start justify-between gap-3"><div><h1 className="text-2xl font-semibold">{es.formats.title}</h1><p className="mt-2 max-w-2xl text-muted-foreground">{es.formats.intro}</p></div>
      {onBack && <Button variant="outline" disabled={editor.dirty || editor.busy} onClick={onBack}>{es.formats.back}</Button>}</header>
    {editor.error && <Alert id="format-error" variant="destructive"><AlertTitle>{es.formats.error}</AlertTitle><AlertDescription>{editor.error}</AlertDescription></Alert>}
    {editor.busy && <div role="status" className="space-y-2"><p>{es.formats.preparing}</p>{editor.progress !== null && <Progress value={editor.progress} aria-label={es.formats.preparing} />}
      {editor.jobId && <Button variant="outline" onClick={() => editor.cancel(actor)}>{es.formats.cancel}</Button>}</div>}
    <div className="grid items-start gap-6 lg:grid-cols-[13rem_minmax(0,1fr)]">
      <aside className="rounded-xl border bg-card p-4 space-y-5" aria-label={es.formats.library}>
        <h2 className="font-semibold">{es.formats.library}</h2>
        <form className="space-y-2" onSubmit={e => { e.preventDefault(); void editor.search(query); }}>
          <label className="block text-sm">{es.formats.searchHelp}<Input className="min-h-11" maxLength={200} value={query} onChange={e => setQuery(e.target.value)} /></label>
          <Button variant="outline" disabled={editor.busy || editor.dirty}>{es.formats.search}</Button>
        </form>
        {editor.status === "loading" && !editor.formats.length && <p role="status">{es.formats.loading}</p>}
        {editor.status === "empty" && !editor.formats.length && <p className="text-sm">{query || editor.offset ? es.formats.noMatches : es.formats.empty}</p>}
        <ul className="space-y-2">{editor.formats.map(format => <li key={format.id}><Button variant={editor.detail?.id === format.id ? "secondary" : "ghost"} className="w-full h-auto min-h-11 whitespace-normal justify-start text-left"
          aria-pressed={editor.detail?.id === format.id} disabled={editor.busy || editor.dirty} onClick={() => { setRegion(null); void editor.open(format.id); }}>{format.name}</Button></li>)}</ul>
        <div className="flex flex-wrap gap-2"><Button variant="ghost" className="h-auto min-h-11 w-full whitespace-normal" disabled={editor.busy || editor.dirty} onClick={() => void editor.reload()}>{es.formats.refresh}</Button>
          {editor.formats.length >= 50 && <Button variant="ghost" disabled={editor.busy || editor.dirty} onClick={() => void editor.moreFormats()}>{es.formats.more}</Button>}
          {editor.offset > 0 && <Button variant="ghost" className="h-auto min-h-11 w-full whitespace-normal" disabled={editor.busy || editor.dirty} onClick={() => void editor.reload()}>{es.formats.first}</Button>}</div>
        <div className="border-t pt-4">
        <form className="space-y-2" onSubmit={e => { e.preventDefault(); void editor.create(name.trim(), actor); }}>
          <label className="block text-sm">{es.formats.name}<Input className="min-h-11" required minLength={1} maxLength={200} value={name} onChange={e => setName(e.target.value)} /></label>
          <Button variant="outline" className="w-full min-h-11" disabled={blocked || !name.trim() || editor.dirty}>{es.formats.create}</Button>
        </form>
        </div>
      </aside>
      <section className="min-w-0 space-y-4" aria-describedby={editor.error ? "format-error" : undefined}>
        {version && <FormatVersionToolbar editor={editor} actor={actor} />}
        <div className="flex flex-wrap gap-3 items-end rounded-xl border bg-card p-4"><div className="flex-1 min-w-0 basis-48 space-y-1">
          <label htmlFor={exampleId} className="block text-sm">{es.formats.examples}</label>
          <SelectField id={exampleId} value={String(editor.documentId ?? "none")} disabled={editor.busy}
            options={[
              { value: "none", label: es.formats.choose },
              ...(editor.documentId !== null && !editor.examples.some(item => item.document_id === editor.documentId)
                ? [{ value: String(editor.documentId), label: `PDF #${editor.documentId}` }] : []),
              ...editor.examples.filter(item => !item.source_file_name?.toLowerCase().endsWith(".xlsx")).map(item => ({
                value: String(item.document_id), label: item.source_file_name ?? item.certificate_no ?? `PDF #${item.document_id}`,
              })),
            ]}
            onChange={value => { const item = editor.examples.find(item => item.document_id === Number(value)); if (item) { editor.selectExample(item.document_id, item.id); setPageNumber(1); setRegion(null); } }} />
        </div>
          {editor.cursor && <Button variant="outline" disabled={editor.busy} onClick={() => void editor.moreExamples()}>{es.formats.moreExamples}</Button>}
          <Button variant="outline" disabled={blocked || !editor.documentId} onClick={() => void editor.prepare(actor)}>{es.formats.prepare}</Button>
        </div>
        {!version && <div className="rounded-xl border border-dashed bg-card p-8"><h2 className="text-lg font-semibold">{es.formats.startTitle}</h2><p className="mt-2 max-w-prose text-sm text-muted-foreground">{es.formats.startHelp}</p></div>}
        {version && configuration && <>
          <div className="grid items-start gap-4 xl:grid-cols-[minmax(0,1fr)_19rem]">
            <div className="min-w-0 rounded-xl border border-border bg-muted/40 p-4 space-y-4">{page && editor.layout ? <>
              <div className="flex flex-wrap gap-3"><div className="text-sm"><label htmlFor={`${selectId}-page`} className="block text-sm mb-1">{es.formats.page}</label>
      <SelectField id={`${selectId}-page`} value={String(page.page_number)} options={editor.layout.document.pages.map(p => ({ value: String(p.page_number), label: String(p.page_number) }))} onChange={next => { setPageNumber(Number(next)); setRegion(null); }} /></div>
                <div className="text-sm"><label htmlFor={`${selectId}-zoom`} className="block text-sm mb-1">{es.formats.zoom}</label>
      <SelectField id={`${selectId}-zoom`} value={String(zoom)} options={[100, 125, 150, 200].map(v => ({ value: String(v), label: `${v}%` }))} onChange={next => { setZoom(Number(next)); }} /></div>
              </div>
              <PageRegionSurface key={`${editor.layout.id}:${page.page_number}`} layoutId={editor.layout.id} page={page} region={region} zoom={zoom} onSelect={setRegion} />
            </> : <p className="rounded-lg border p-6 text-muted-foreground">{editor.layout ? es.formats.noPages : es.formats.noLayout}</p>}</div>
            <div className="min-w-0 rounded-xl border bg-card p-4"><MappingPanel configuration={configuration} onChange={editor.setConfiguration} page={page} region={region} onRegion={setRegion} disabled={editor.busy || version.status !== "draft"} /></div>
          </div>
          {editor.applied && onOpenRevision && <Button variant="outline" onClick={() => { if (editor.applied) onOpenRevision(editor.applied.certificate_id); }}>{es.formats.openRevision}</Button>}
          <FormatTestResults tests={editor.tests} busy={blocked} dirty={editor.dirty} layoutId={editor.layout?.id ?? null} onInspect={test => { setRegion(null); setPageNumber(1); void editor.inspectTest(test); }} onConfirm={id => void editor.confirm(id, actor)} />
        </>}
      </section>
    </div>
  </div></div>;
}
