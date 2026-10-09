import { Spinner } from "@/components/ui/spinner";
import { es } from "@/lib/i18n";
import { isTerminalPhase, type ImportItem } from "../model/importItem";

export function ProcessingNotice({ items }: { items: readonly ImportItem[] }) {
  const count = items.filter((item) => !isTerminalPhase(item.phase)).length;
  if (!count) return null;
  return <div className="flex shrink-0 flex-wrap items-center justify-between gap-3 border-b border-blue-200 bg-blue-50 px-4 py-2">
    <p role="status" className="flex items-center gap-2 text-sm text-blue-900"><Spinner aria-hidden="true" />{es.workspace.activeJobs(count)}</p>
  </div>;
}
