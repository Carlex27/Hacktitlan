import { Button } from "@/components/ui/button";
import type { FormatTestDto, JsonValue, MappingTargetDto } from "@/lib/api";
import { es } from "@/lib/i18n";
import { previewRows } from "../model/previewRows";

function display(value: JsonValue | undefined): string {
  if (value === null || value === undefined) return es.formats.unknownValue;
  if (typeof value === "boolean") return value ? es.workspace.yes : es.workspace.no;
  return typeof value === "object" ? JSON.stringify(value) : String(value);
}
function fieldLabel(field: string) {
  return field.startsWith("chemistry.") ? `${es.formats.chemistry}: ${field.slice(10)}` : es.formats.targets[field as MappingTargetDto] ?? field;
}
function DataRows({ result }: { result: NonNullable<FormatTestDto["result"]> }) {
  return <div className="overflow-x-auto" tabIndex={0} aria-label={es.formats.result}><table className="w-full text-sm text-left"><thead><tr>
    {[es.formats.product, es.formats.field, es.formats.original, es.formats.normalized, es.formats.page].map(label => <th className="p-2" key={label}>{label}</th>)}</tr></thead>
    <tbody>{previewRows(result).map((row, index) => <tr className="border-t" key={index}><td className="p-2">{row.product ?? "—"}</td><td className="p-2">{fieldLabel(row.field)}</td>
      <td className="p-2 break-all">{display(row.original)}</td><td className="p-2 break-all">{display(row.normalized)} {row.normalized !== null ? row.field.startsWith("chemistry.") ? "%" : es.formats.targetUnits[row.field] : ""}</td><td className="p-2">{row.page ?? "—"}</td></tr>)}</tbody></table></div>;
}
export function FormatTestResults({ tests, busy, dirty, layoutId, onInspect, onConfirm }: { tests: FormatTestDto[]; busy: boolean; dirty: boolean; layoutId: number | null; onInspect(test: FormatTestDto): void; onConfirm(id: number): void }) {
  return <section className="space-y-4 border-t pt-6"><h2 className="text-lg font-semibold">{es.formats.tests}</h2>
    {!tests.length && <p>{es.formats.noTests}</p>}
    {tests.map(test => <article key={test.id} className="border rounded-lg p-4 space-y-3">
      <h3 className="font-medium">PDF #{test.document_id} · {es.formats.statuses[test.status]}</h3>
      <Button variant="outline" disabled={busy} onClick={() => onInspect(test)}>{es.formats.inspect}</Button>
      {(!test.current_revision || dirty) && <p className="text-warning-foreground">{es.formats.obsolete}</p>}
      {test.result?.diagnostics.length ? <div role="status"><h4 className="font-medium">{es.formats.diagnostics}</h4><ul className="list-disc pl-5">{test.result.diagnostics.map((d, i) => <li key={i}>{d.field}: {d.message} {d.page_number !== null ? `· ${es.formats.page} ${d.page_number}` : ""}</li>)}</ul></div> : null}
      {test.result?.status === "empty" && <p>{es.formats.emptyResult}</p>}
      {test.result?.status === "success" && <p role="status">{es.formats.success}</p>}
      {test.result?.certificate && <details><summary className="cursor-pointer focus-visible:outline focus-visible:outline-ring">{es.formats.result}</summary><DataRows result={test.result} /></details>}
      {test.result?.evidence.length ? <details><summary className="cursor-pointer focus-visible:outline focus-visible:outline-ring">{es.formats.evidence}</summary><ul className="space-y-2 pt-3 text-sm">{test.result.evidence.map((e, i) => <li key={i}>
        {fieldLabel(String(e.field))}: {display(e.raw_value)} · {es.formats.page} {display(e.page_number)} · {e.geometry_scope === "table" ? es.formats.tableScope : es.formats.region}
      </li>)}</ul></details> : null}
      {test.reviewed_by ? <p>{es.formats.reviewed}: {test.reviewed_by}</p> : <Button variant="outline" disabled={busy || dirty || layoutId !== test.layout_id || !test.current_revision || test.result?.status !== "success" || test.status !== "succeeded"} onClick={() => onConfirm(test.id)}>{es.formats.confirm}</Button>}
    </article>)}
  </section>;
}
