import { useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { usePdfObjectUrl } from "@/features/document-viewer";
import type { PageLayoutDto, RegionDto } from "@/lib/api";
import { es } from "@/lib/i18n";
import { regionFromPoints, regionStyle, relativeBox, validRegion } from "../model/geometry";

export function PageRegionSurface({ layoutId, page, region, zoom, onSelect }: {
  layoutId: number; page: PageLayoutDto; region: RegionDto | null; zoom: number;
  onSelect(region: RegionDto): void;
}) {
  const { state, reload } = usePdfObjectUrl(`/api/v1/document-layouts/${layoutId}/pages/${page.page_number}/image`);
  const start = useRef<{ x: number; y: number } | null>(null);
  const [drawing, setDrawing] = useState<RegionDto | null>(null);
  const point = (event: React.PointerEvent<HTMLDivElement>) => {
    const rect = event.currentTarget.getBoundingClientRect();
    return { x: (event.clientX - rect.left) / rect.width, y: (event.clientY - rect.top) / rect.height };
  };
  const visible = drawing ?? region;
  return <section className="space-y-3 min-w-0" aria-label={es.formats.selection}>
    <p className="text-sm text-muted-foreground">{es.formats.selectHelp}</p>
    {page.source === "unreadable" && <p role="status">{es.formats.unreadable}</p>}
    {state.status === "loading" && <p role="status">{es.formats.loading}</p>}
    {state.status === "error" && <div role="alert">{es.formats.imageError} <Button onClick={reload}>{es.formats.retry}</Button></div>}
    {state.status === "ready" && <div className="overflow-auto border rounded-lg max-h-[75vh]" tabIndex={0} aria-label={es.formats.page}>
      <div className="relative touch-none select-none" style={{ width: `${zoom}%` }}
        onPointerDown={event => { if (event.button !== 0) return; start.current = point(event); event.currentTarget.setPointerCapture(event.pointerId); }}
        onPointerMove={event => { if (start.current) setDrawing(regionFromPoints(start.current, point(event))); }}
        onPointerUp={event => { if (start.current) { const next = regionFromPoints(start.current, point(event)); if (next) onSelect(next); }
          start.current = null; setDrawing(null); }}
        onPointerCancel={() => { start.current = null; setDrawing(null); }}>
        <img src={state.objectUrl} alt={`${es.formats.page} ${page.page_number}`} className="block w-full" draggable={false} />
        {visible && validRegion(visible) && <div className="pointer-events-none absolute border-2 border-primary bg-primary/10" style={regionStyle(visible)} />}
      </div>
    </div>}
    <details className="border rounded-lg p-3"><summary className="cursor-pointer focus-visible:outline focus-visible:outline-ring">{es.formats.blocks}</summary>
      <div className="max-h-56 overflow-auto mt-3 space-y-2">{page.blocks.map((block, index) => <Button key={index} variant="outline"
        className="h-auto min-h-11 w-full justify-start whitespace-normal text-left" onClick={() => onSelect(relativeBox(block.bbox, page))}
        aria-label={`${es.formats.block}: ${block.text}`}>{block.text}</Button>)}
        {page.tables.map((table, index) => <Button key={`t${index}`} variant="outline" onClick={() => onSelect(relativeBox(table.bbox, page))}>
          {es.formats.table} {index + 1}</Button>)}</div>
    </details>
  </section>;
}
