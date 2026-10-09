import { SelectField } from "@/components/ui";
import { useId } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { TableMappingDto } from "@/lib/api";
import { es } from "@/lib/i18n";
import { emptyMapping } from "../model/mappings";
import { MappingValueForm } from "./MappingValueForm";

export function TableMappingForm({ table, onChange, disabled = false }: { table: TableMappingDto; onChange(table: TableMappingDto): void; disabled?: boolean }) {
  const selectId = useId();
  return <div className="space-y-4 text-sm"><div className="grid grid-cols-2 gap-3">
    <div><label htmlFor={`${selectId}-role`} className="block text-sm mb-1">{es.formats.role}</label>
      <SelectField id={`${selectId}-role`} value={table.role} options={(["products", "chemistry", "mechanical"] as const).map(role => ({ value: role, label: es.formats[role] }))} disabled={disabled} onChange={next => { onChange({ ...table, role: next as TableMappingDto["role"] }); }} /></div>
    <div><label htmlFor={`${selectId}-join`} className="block text-sm mb-1">{es.formats.join}</label>
      <SelectField id={`${selectId}-join`} value={table.join_key} options={[{ value: "product_id", label: es.formats.targets.product_id }, { value: "heat_no", label: es.formats.targets.heat_no }]} disabled={disabled} onChange={next => { onChange({ ...table, join_key: next as TableMappingDto["join_key"] }); }} /></div>
    <label>{es.formats.headerRow}<Input className="min-h-11" type="number" min={1} max={101} value={table.header_row + 1} onChange={e => onChange({ ...table, header_row: e.target.valueAsNumber - 1 })} /></label>
  </div><p className="text-muted-foreground">{es.formats.tableHelp}</p>
    {table.columns.map((column, index) => <fieldset key={index} className="border-t pt-3 space-y-2"><legend>{es.formats.columns} {index + 1}</legend>
      <label>{es.formats.header}<Input className="min-h-11" required value={column.header} onChange={e => onChange({ ...table, columns: table.columns.map((c, i) => i === index ? { ...c, header: e.target.value } : c) })} /></label>
      <MappingValueForm disabled={disabled} columns value={column} onChange={value => onChange({ ...table, columns: table.columns.map((c, i) => i === index ? { ...value, header: column.header } : c) })} />
      <Button variant="ghost" onClick={() => onChange({ ...table, columns: table.columns.filter((_, i) => i !== index) })}>{es.formats.remove}</Button>
    </fieldset>)}
    <Button variant="outline" onClick={() => onChange({ ...table, columns: [...table.columns, { ...emptyMapping("product_id"), header: "" }] })}>{es.formats.addColumn}</Button>
  </div>;
}
