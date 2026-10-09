import { useId, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { DatePicker, SelectField } from "@/components/ui";
import type { CertificateFilters } from "@/lib/api";
import { es } from "@/lib/i18n";

const groups = [
  { title: "documentFilters", fields: [
    ["certificate_no", "certificate", "text"], ["manufacturer", "manufacturer", "text"],
  ] },
  { title: "productFilters", fields: [
    ["heat_no", "heat", "text"], ["product_identifier", "roll", "text"],
    ["fraction", "fraction", "text"], ["nico", "nicoFilter", "text"],
  ] },
  { title: "dateStatusFilters", fields: [
    ["date_from", "from", "date"], ["date_to", "to", "date"],
  ] },
] as const;

export function CertificateFiltersForm({ onApply }: { onApply(filters: CertificateFilters): void }) {
  const id = useId();
  const [filters, setFilters] = useState<CertificateFilters>({});
  return <form aria-label={es.workspace.filters} aria-describedby={`${id}-hint`} className="space-y-5 border-b border-border pb-6"
    onSubmit={(event) => { event.preventDefault(); onApply(filters); }}>
    <h3 className="text-base leading-6 font-semibold">{es.workspace.filters}</h3>
    <p id={`${id}-hint`} className="text-sm leading-5 text-muted-foreground">{es.workspace.filtersHint}</p>
    {groups.map((group) => <fieldset key={group.title} className="min-w-0 space-y-3">
      <legend className="mb-3 text-sm font-semibold">{es.workspace[group.title]}</legend>
      <div className={`grid gap-4 sm:grid-cols-2 ${group.title === "productFilters" ? "lg:grid-cols-4" : group.title === "dateStatusFilters" ? "lg:grid-cols-3" : ""}`}>
    {group.fields.map(([key, label, type]) => <div key={key} className="min-w-0">
      <label htmlFor={`${id}-${key}`} className="mb-2 block text-sm leading-5 font-medium">{es.workspace[label]}</label>
      {type === "date" ? <DatePicker id={`${id}-${key}`} label={es.workspace[label]} value={filters[key] ?? ""}
        {...(key === "date_to" && filters.date_from ? { min: filters.date_from } : {})}
        {...(key === "date_from" && filters.date_to ? { max: filters.date_to } : {})}
        onChange={(value) => setFilters({ ...filters, [key]: value })} /> :
      <Input className="h-11 min-w-0 bg-background" id={`${id}-${key}`} type={type} value={filters[key] ?? ""}
        {...(key === "certificate_no" ? { placeholder: es.workspace.certificateSearchHint } : {})}
        onChange={(event) => setFilters({ ...filters, [key]: event.target.value })} />}
    </div>)}
    {group.title === "dateStatusFilters" && <div className="min-w-0 sm:col-span-2 lg:col-span-1"><label htmlFor={`${id}-status`} className="mb-2 block text-sm leading-5 font-medium">{es.workspace.approval}</label>
      <SelectField id={`${id}-status`} value={filters.approval_status || "all"}
        options={[{ value: "all", label: es.workspace.all }, ...Object.entries(es.workspace.status).map(([value, label]) => ({ value, label }))]}
        onChange={(value) => setFilters({ ...filters,
          approval_status: (value === "all" ? "" : value) as Exclude<CertificateFilters["approval_status"], undefined> })} /></div>}
    </div>
    {group.title === "dateStatusFilters" && <p className="text-sm text-muted-foreground">{es.workspace.dateFilterHint}</p>}
    </fieldset>)}
    <div className="flex flex-col gap-2 border-t border-border pt-4 sm:flex-row">
      <Button className="min-h-11" type="submit">{es.workspace.apply}</Button>
      <Button className="min-h-11" type="button" variant="outline" onClick={() => { setFilters({}); onApply({}); }}>{es.workspace.clear}</Button>
    </div>
  </form>;
}
