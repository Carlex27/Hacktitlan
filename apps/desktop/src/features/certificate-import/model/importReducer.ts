import type { JobDto, UploadDocumentDto } from "@/lib/api";

import {
  applyFailure,
  applyJob,
  applyUpload,
  isTerminalPhase,
  type ImportItem,
} from "./importItem";

export type ImportAction =
  | { type: "added"; items: readonly ImportItem[] }
  | { type: "uploaded"; id: string; upload: UploadDocumentDto }
  | { type: "job_updated"; id: string; job: JobDto }
  | { type: "failed"; id: string; message: string }
  | { type: "finished_cleared" };

function updateItem(
  items: readonly ImportItem[],
  id: string,
  update: (item: ImportItem) => ImportItem,
): readonly ImportItem[] {
  return items.map((item) => (item.id === id ? update(item) : item));
}

export function importReducer(
  items: readonly ImportItem[],
  action: ImportAction,
): readonly ImportItem[] {
  switch (action.type) {
    case "added":
      return [...action.items, ...items];
    case "uploaded":
      return updateItem(items, action.id, (item) => applyUpload(item, action.upload));
    case "job_updated":
      return updateItem(items, action.id, (item) => applyJob(item, action.job));
    case "failed":
      return updateItem(items, action.id, (item) => applyFailure(item, action.message));
    case "finished_cleared":
      return items.filter((item) => !isTerminalPhase(item.phase));
  }
}
