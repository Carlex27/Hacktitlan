import { SelectField } from "@/components/ui";
import { useId } from "react";
import { Input } from "@/components/ui/input";
import type { MappingTargetDto, ValueMappingDto } from "@/lib/api";
import { es } from "@/lib/i18n";
import { emptyMapping } from "../model/mappings";

export function MappingValueForm({ value, onChange, columns = false, disabled = false }: { value: ValueMappingDto; onChange(value: ValueMappingDto): void; columns?: boolean; disabled?: boolean }) {
  const selectId = useId();
  return <div className="grid grid-cols-2 gap-3 text-sm">
    <div className="col-span-2 space-y-1"><label htmlFor={`${selectId}-field`} className="block text-sm mb-1">{es.formats.field}</label>
      <SelectField id={`${selectId}-field`} value={value.target} options={(Object.keys(es.formats.targets) as MappingTargetDto[]).filter(target => !columns || !["certificate_no", "supplier", "standard"].includes(target)).map(target => ({ value: target, label: es.formats.targets[target] }))} disabled={disabled} onChange={next => { onChange(emptyMapping(next as MappingTargetDto)); }} /></div>
    {value.unit !== null && <><div><label htmlFor={`${selectId}-unit`} className="block text-sm mb-1">{es.formats.unit}</label>
      <SelectField id={`${selectId}-unit`} value={value.unit} options={(value.unit === "mm" || ["thickness_mm", "width_mm", "length_raw"].includes(value.target) ? ["mm", "cm", "in", "ft", "m"] : [value.unit]).map(unit => ({ value: unit, label: unit }))} disabled={disabled} onChange={next => { onChange({ ...value, unit: next as ValueMappingDto["unit"] }); }} /></div><div><label htmlFor={`${selectId}-decimal`} className="block text-sm mb-1">{es.formats.decimal}</label>
      <SelectField id={`${selectId}-decimal`} value={value.decimal_separator} options={[{ value: ".", label: "." }, { value: ",", label: "," }]} disabled={disabled} onChange={next => { onChange({ ...value, decimal_separator: next as "." | "," }); }} /></div></>}
    {value.target === "chemistry" && <><label>{es.formats.element}<Input className="min-h-11" required value={value.element ?? ""} onChange={event => onChange({ ...value, element: event.target.value })} /></label>
      <label>{es.formats.exponent}<Input className="min-h-11" type="number" min={-6} max={6} required value={value.exponent ?? ""} onChange={event => onChange({ ...value, exponent: event.target.valueAsNumber })} /></label></>}
    <label className="flex gap-2 items-center col-span-2 min-h-11"><input type="checkbox" checked={value.required} onChange={event => onChange({ ...value, required: event.target.checked })} />{es.formats.required}</label>
  </div>;
}
