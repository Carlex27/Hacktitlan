import { Input } from "@/components/ui/input";
import { useId } from "react";
import type { RegionDto } from "@/lib/api";
import { es } from "@/lib/i18n";
import { validRegion } from "../model/geometry";

export function RegionControls({ region, onChange }: { region: RegionDto; onChange(region: RegionDto): void }) {
  const valid = validRegion(region);
  const errorId = useId();
  return <fieldset className="space-y-3"><legend className="font-medium">{es.formats.selection}</legend>
    <div className="grid grid-cols-2 gap-3">{(["x0", "top", "x1", "bottom"] as const).map(key =>
      <label key={key} className="space-y-1 text-sm">{es.formats[key]}<Input className="min-h-11" type="number" min={0} max={100} step={0.1}
        value={Number.isFinite(region[key]) ? Number((region[key] * 100).toFixed(3)) : ""} aria-invalid={!valid}
        aria-describedby={!valid ? errorId : undefined} onChange={event => onChange({ ...region, [key]: event.target.valueAsNumber / 100 })} /></label>)}</div>
    {!valid && <p id={errorId} role="alert" className="text-destructive text-sm">{es.formats.regionError}</p>}
  </fieldset>;
}
