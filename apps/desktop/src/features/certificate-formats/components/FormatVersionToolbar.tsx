import { SelectField } from "@/components/ui";
import { useId } from "react";
import { Button } from "@/components/ui/button";
import type { ActorReasonDto } from "@/lib/api";
import { es } from "@/lib/i18n";
import type { FormatEditorController } from "../hooks/useFormatEditor";

export function FormatVersionToolbar({ editor, actor }: { editor: FormatEditorController; actor: ActorReasonDto }) {
  const selectId = useId();
  const { version } = editor;
  if (!version) return null;
  const blocked = editor.busy || editor.status === "loading";
  return <header aria-label={es.formats.versionActions} className="rounded-xl border bg-card p-4 space-y-4">
    <div className="flex flex-wrap items-center gap-4"><h2 className="text-lg font-semibold">{editor.detail?.name}</h2>
      <div className="min-w-40 text-sm"><label htmlFor={`${selectId}-version`} className="block text-sm mb-1">{es.formats.version}</label>
      <SelectField id={`${selectId}-version`} value={String(version.id)} options={editor.detail?.versions.map(v => ({ value: String(v.id), label: `${v.version_number} · ${es.formats.statuses[v.status]}` })) ?? []} disabled={editor.busy || editor.dirty} onChange={next => { editor.selectVersion(Number(next)); }} /></div>
      <p role="status" className="text-sm text-muted-foreground">{editor.dirty ? es.formats.dirty : es.formats.saved}</p>
    </div>
    <div className="space-y-3"><div className="flex flex-wrap gap-2">
      {version.status === "draft" ? <><Button className="min-h-11" variant="outline" disabled={blocked || !editor.dirty} onClick={() => void editor.save(actor)}>{es.formats.save}</Button>
        <Button className="min-h-11" disabled={blocked || !editor.layout} onClick={() => void editor.test(actor)}>{es.formats.test}</Button>
        <Button className="min-h-11" variant="outline" disabled={blocked || editor.dirty} onClick={() => void editor.transition("activate", actor)}>{es.formats.activate}</Button></> : <>
        <Button className="min-h-11" disabled={blocked} onClick={() => void editor.newVersion(actor)}>{es.formats.newVersion}</Button>
        {version.status === "active" && <><Button className="min-h-11" variant="outline" disabled={blocked} onClick={() => void editor.transition("retire", actor)}>{es.formats.retire}</Button>
          <Button className="min-h-11" variant="outline" disabled={blocked || !editor.certificateId} onClick={() => void editor.apply(actor)}>{es.formats.apply}</Button></>}
      </>}
    </div><p className="text-sm text-muted-foreground">{es.formats.activationHelp}</p>
    </div>
  </header>;
}
