import type { JobDto } from "@/lib/api";

export function nextPollInterval(previous: JobDto | null, current: JobDto, interval: number, base: number): number {
  return previous !== null && previous.status === current.status && previous.progress === current.progress
    ? Math.min(interval * 2, base * 4)
    : base;
}
