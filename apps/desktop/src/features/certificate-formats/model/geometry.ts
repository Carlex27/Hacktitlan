import type { PageLayoutDto, RegionDto } from "@/lib/api";

const clamp = (value: number) => Math.max(0, Math.min(1, value));
export function regionFromPoints(start: { x: number; y: number }, end: { x: number; y: number }): RegionDto | null {
  const region = { x0: clamp(Math.min(start.x, end.x)), top: clamp(Math.min(start.y, end.y)),
    x1: clamp(Math.max(start.x, end.x)), bottom: clamp(Math.max(start.y, end.y)) };
  return region.x1 > region.x0 && region.bottom > region.top ? region : null;
}
export function relativeBox(box: RegionDto, page: PageLayoutDto): RegionDto {
  return { x0: box.x0 / page.width, x1: box.x1 / page.width, top: box.top / page.height, bottom: box.bottom / page.height };
}
export function regionStyle(region: RegionDto) {
  return { left: `${region.x0 * 100}%`, top: `${region.top * 100}%`,
    width: `${(region.x1 - region.x0) * 100}%`, height: `${(region.bottom - region.top) * 100}%` };
}
export function validRegion(region: RegionDto): boolean {
  return Object.values(region).every(v => Number.isFinite(v) && v >= 0 && v <= 1) && region.x0 < region.x1 && region.top < region.bottom;
}
