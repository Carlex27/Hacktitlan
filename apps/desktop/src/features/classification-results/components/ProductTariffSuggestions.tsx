import { LoadErrorAlert } from "@/components/feedback";
import type { ClassificationResultDto } from "@/lib/api";
import { es } from "@/lib/i18n";

export interface ProductTariffSuggestionsProps {
  result: ClassificationResultDto | undefined;
  isLoading: boolean;
  error: unknown;
  onRetry?: () => void;
}

export function ProductTariffSuggestions({ result, isLoading, error, onRetry }: ProductTariffSuggestionsProps) {
  const text = es.certificateReview.products;
  if (isLoading) return <p role="status">{text.loadingSuggestions}</p>;
  if (error) return <LoadErrorAlert title={es.classification.loadError} error={error} {...(onRetry ? { onRetry } : {})} />;
  return <div className="mt-2 space-y-1">
    <p className="font-semibold">{text.suggestions}</p>
    {result?.fraction && result.nico && result.current_selection &&
      <p>{text.selectedTariff}: {text.fraction} {result.fraction} · {text.nico} {result.nico}</p>}
    {result?.candidates.length ? <ul aria-label={text.suggestions} className="space-y-1">
      {result.candidates.map((candidate) => <li key={candidate.id} className="flex flex-wrap gap-x-3 gap-y-1">
        <span>{text.fraction} <strong className="font-mono">{candidate.fraction}</strong></span>
        <span>{text.nico} <strong className="font-mono">{candidate.nico}</strong></span>
        <span>{es.classification.supportLevel[candidate.support_level] ?? candidate.support_level}</span>
      </li>)}
    </ul> : <p className="text-slate-500">{text.noSuggestions}</p>}
    {result?.outcome === "needs_review" && <p className="text-amber-700">{text.needsReview}</p>}
  </div>;
}
