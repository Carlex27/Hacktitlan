import { FactorEvidenceButton } from "./FactorEvidenceButton";
import type { ClassificationCandidateDto } from "@/lib/api";
import { es } from "@/lib/i18n";
import { formatFactorValue, readSourceReference, type TariffActionRenderer } from "../model";

export function CandidateFactors({ candidate, onViewEvidence, renderTariffAction }: {
  candidate: ClassificationCandidateDto | undefined;
  onViewEvidence?: ((id: number) => void) | undefined;
  renderTariffAction?: TariffActionRenderer | undefined;
}) {
  if (!candidate) return null;
  const text = es.workspace;
  return <section aria-label={text.conditions} className="space-y-4">
    <h4 className="text-sm font-semibold">{text.conditions}: {candidate.fraction} · NICO {candidate.nico}</h4>
    {candidate.factors.length === 0 ? <p className="text-sm text-muted-foreground">{text.noFactors}</p> :
      candidate.factors.map((factor) => <details key={factor.id} className="border-b border-border py-3">
        <summary className="min-h-11 cursor-pointer py-2 text-sm leading-6 font-medium focus-visible:outline-2 focus-visible:outline-primary">
          {factor.explanation || factor.rule_code} · {text.factorStatus[factor.outcome]}
        </summary>
        <dl className="mt-3 grid gap-4 text-sm leading-6 sm:grid-cols-2"><div><dt className="font-medium text-muted-foreground">{text.expected}</dt><dd className="break-words">{formatFactorValue(factor.expected, factor.unit).map((line, index) => <p key={index}>{line}</p>)}</dd></div>
          <div><dt className="font-medium text-muted-foreground">{text.observed}</dt><dd className="break-words">{formatFactorValue(factor.observed, factor.unit).map((line, index) => <p key={index}>{line}</p>)}</dd></div>
        </dl>
        <div className="mt-3 flex flex-wrap gap-2">
          {onViewEvidence && <FactorEvidenceButton links={factor.evidence_links} onOpen={onViewEvidence} />}
          {factor.evidence_links.map((link) => <div key={link.id} className="flex gap-2">
          {link.source_type === "rule_source" && renderTariffAction?.(readSourceReference(link.reference), factor.rule_code)}
        </div>)}</div>
      </details>)}
  </section>;
}
