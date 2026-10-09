import { SelectField } from "@/components/ui";
import { useId, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { PageLayoutDto, RegionDto, TemplateConfigurationDto, ValueMappingDto } from "@/lib/api";
import { es } from "@/lib/i18n";
import { emptyMapping } from "../model/mappings";
import { relativeBox, validRegion } from "../model/geometry";
import { RegionControls } from "./RegionControls";
import { MappingValueForm } from "./MappingValueForm";
import { TableMappingForm } from "./TableMappingForm";

export function MappingPanel({ configuration: config, onChange, page, region, onRegion, disabled }: {
  configuration: TemplateConfigurationDto; onChange(config: TemplateConfigurationDto): void;
  page: PageLayoutDto | null; region: RegionDto | null; onRegion(region: RegionDto): void; disabled: boolean;
}) {
  const selectId = useId();
  const [mapping, setMapping] = useState<ValueMappingDto>(emptyMapping());
  const [anchor, setAnchor] = useState("");
  const selectable = page !== null && region !== null && validRegion(region);
  const addTable = () => {
    if (!page || !region) return;
    const found = page.tables.find(t => { const box = relativeBox(t.bbox, page); return box.x0 >= region.x0 && box.x1 <= region.x1 && box.top >= region.top && box.bottom <= region.bottom; });
    onChange({ ...config, tables: [...config.tables, { page_number: page.page_number, region, role: "products", join_key: "product_id", header_row: 0,
      columns: [{ ...emptyMapping("product_id"), header: found?.rows[0]?.find(cell => !!cell) ?? "" }] }] });
  };
  return <fieldset disabled={disabled} className="space-y-6 min-w-0"><legend className="sr-only">{es.formats.mappings}</legend>
    {region && <RegionControls region={region} onChange={onRegion} />}
    <section className="space-y-3"><h3 className="font-semibold">{es.formats.assignZone}</h3>
      {!selectable && <p id="format-zone-help" className="text-sm text-muted-foreground">{es.formats.selectZoneFirst}</p>}<MappingValueForm disabled={disabled} value={mapping} onChange={setMapping} />
      <Button className="w-full min-h-11" aria-describedby={!selectable ? "format-zone-help" : undefined} disabled={!selectable} onClick={() => { if (page && region) onChange({ ...config, fields: [...config.fields, { ...mapping, page_number: page.page_number, region }] }); }}>{es.formats.addField}</Button>
      <Button variant="outline" className="w-full min-h-11" aria-describedby={!selectable ? "format-zone-help" : undefined} disabled={!selectable} onClick={addTable}>{es.formats.addTable}</Button>
    </section>
    <section className="border-t pt-5 space-y-3"><h3 className="font-semibold">{es.formats.mappings}</h3>
      {!config.fields.length && !config.tables.length && <p className="text-sm text-muted-foreground">{es.formats.noMappings}</p>}
      {config.fields.map((field, index) => <details key={index} className="border-t py-3"><summary className="cursor-pointer focus-visible:outline focus-visible:outline-ring">{es.formats.targets[field.target]} {field.element} · {es.formats.page} {field.page_number}</summary>
        <div className="space-y-3 pt-3"><MappingValueForm disabled={disabled} value={field} onChange={value => onChange({ ...config, fields: config.fields.map((f, i) => i === index ? { ...value, page_number: field.page_number, region: field.region } : f) })} />
          <RegionControls region={field.region} onChange={value => onChange({ ...config, fields: config.fields.map((f, i) => i === index ? { ...f, region: value } : f) })} />
          <Button variant="ghost" onClick={() => onChange({ ...config, fields: config.fields.filter((_, i) => i !== index) })}>{es.formats.remove}</Button></div>
      </details>)}
      {config.tables.map((table, index) => <details key={index} className="border-t py-3"><summary className="cursor-pointer focus-visible:outline focus-visible:outline-ring">{es.formats.tables} {index + 1} · {es.formats.page} {table.page_number}</summary><div className="pt-3 space-y-3">
        <TableMappingForm disabled={disabled} table={table} onChange={value => onChange({ ...config, tables: config.tables.map((t, i) => i === index ? value : t) })} />
        <RegionControls region={table.region} onChange={region => onChange({ ...config, tables: config.tables.map((t, i) => i === index ? { ...t, region } : t) })} />
        <Button variant="ghost" onClick={() => onChange({ ...config, tables: config.tables.filter((_, i) => i !== index) })}>{es.formats.remove}</Button></div>
      </details>)}
    </section>
    <section className="border-t pt-5 space-y-3"><h3 className="font-semibold">{es.formats.anchors}</h3><p className="text-sm text-muted-foreground">{es.formats.anchorHelp}</p>
      <label className="block text-sm">{es.formats.anchorText}<Input className="min-h-11" value={anchor} onChange={e => setAnchor(e.target.value)} /></label>
      <Button variant="outline" disabled={!selectable || anchor.trim().length < 3} onClick={() => { if (page && region) { onChange({ ...config, recognition: [...config.recognition, { text: anchor.trim(), page_number: page.page_number, region }] }); setAnchor(""); } }}>{es.formats.addAnchor}</Button>
      <ul className="space-y-2">{config.recognition.map((a, index) => <li key={index} className="flex flex-wrap items-center gap-2 text-sm">{a.text} · {es.formats.page} {a.page_number}
        <Button variant="ghost" aria-label={`${es.formats.remove}: ${a.text}`} onClick={() => onChange({ ...config, recognition: config.recognition.filter((_, i) => i !== index) })}>{es.formats.remove}</Button></li>)}</ul>
    </section>
    <div className="grid grid-cols-2 gap-3 border-t pt-5 text-sm"><div><label htmlFor={`${selectId}-form`} className="block text-sm mb-1">{es.formats.form}</label>
      <SelectField id={`${selectId}-form`} value={config.form ?? "unknown"} options={[{ value: "unknown", label: es.formats.unknown }, { value: "flat_rolled", label: es.formats.flat }]} disabled={disabled} onChange={next => { onChange({ ...config, form: next === "unknown" ? null : "flat_rolled" }); }} /></div>
      <div><label htmlFor={`${selectId}-rolling`} className="block text-sm mb-1">{es.formats.rolling}</label>
      <SelectField id={`${selectId}-rolling`} value={config.rolling ?? "unknown"} options={[{ value: "unknown", label: es.formats.unknown }, { value: "cold", label: es.formats.cold }, { value: "hot", label: es.formats.hot }]} disabled={disabled} onChange={next => { onChange({ ...config, rolling: next === "unknown" ? null : next as "cold" | "hot" }); }} /></div></div>
  </fieldset>;
}
