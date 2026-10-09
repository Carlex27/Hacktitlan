export function activeSectionIndex(tops: readonly number[], readingLine: number, atBottom: boolean): number {
  if (atBottom) return Math.max(0, tops.length - 1);
  let active = 0;
  tops.forEach((top, index) => { if (top <= readingLine) active = index; });
  return active;
}
