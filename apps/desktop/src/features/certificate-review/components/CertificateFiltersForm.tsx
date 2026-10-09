import { useId, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { CertificateFilters } from "@/lib/api";
import { es } from "@/lib/i18n";

const fields = [
  ["certificate_no", "certificate", "text"], ["manufacturer", "manufacturer", "text"],
  ["heat_no", "heat", "text"], ["product_identifier", "roll", "text"],
  ["fraction", "fraction", "text"], ["nico", "nicoFilter", "text"],
  ["date_from", "from", "date"], ["date_to", "to", "date"],
] as const;

export function CertificateFiltersForm({ onApply }: { onApply(filters: CertificateFilters): void }) {
  const id = useId();
  const [filters, setFilters] = useState<CertificateFilters>({});
  return <form aria-label={es.workspace.filters} className="space-y-4 border-b border-border pb-6"
    onSubmit={(event) => { event.preventDefault(); onApply(filters); }}>
    <h3 className="text-base leading-6 font-semibold">{es.workspace.filters}</h3>
    <div className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,12rem),1fr))] gap-4">
    {fields.map(([key, label, type]) => <div key={key} className="min-w-0">
      <label htmlFor={`${id}-${key}`} className="mb-2 block text-sm leading-5 font-medium">{es.workspace[label]}</label>
      <Input className="h-10 min-w-0 bg-background" id={`${id}-${key}`} type={type} value={filters[key] ?? ""}
        {...(key === "date_to" && filters.date_from ? { min: filters.date_from } : {})}
        onChange={(event) => setFilters({ ...filters, [key]: event.target.value })} />
    </div>)}
    <div className="min-w-0"><label htmlFor={`${id}-status`} className="mb-2 block text-sm leading-5 font-medium">{es.workspace.approval}</label>
      <select id={`${id}-status`} className="h-10 w-full min-w-0 rounded-lg border border-input bg-background px-3 text-sm text-foreground focus-visible:outline-2 focus-visible:outline-primary focus-visible:outline-offset-2"
        value={filters.approval_status ?? ""} onChange={(event) => setFilters({ ...filters,
          approval_status: event.target.value as Exclude<CertificateFilters["approval_status"], undefined> })}>
        <option value="">{es.workspace.all}</option>
        {Object.entries(es.workspace.status).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
      </select></div>
    </div>
    <div className="flex flex-wrap gap-2">
      <Button className="min-h-10" type="submit">{es.workspace.apply}</Button>
      <Button className="min-h-10" type="button" variant="outline" onClick={() => { setFilters({}); onApply({}); }}>{es.workspace.clear}</Button>
    </div>
  </form>;
}
