import { FileText, MapPin, X } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { EvidenceDetailDto } from "@/lib/api";
import { es } from "@/lib/i18n";

import { readSourceReference, type SourceReference } from "../model";

export interface EvidencePanelProps {
  evidence: EvidenceDetailDto | null;
  onClose: () => void;
  onGoToPage?: (page: number) => void;
  /** Abre la fuente normativa citada por una evidencia `rule_source`. */
  onOpenSource?: (reference: SourceReference, label: string) => void;
}

export function EvidencePanel({ evidence, onClose, onGoToPage, onOpenSource }: EvidencePanelProps) {
  if (!evidence) return null;

  const isObservation = evidence.source_type === "observation";
  const obs = isObservation ? evidence.observation : null;
  const focus = isObservation ? evidence.focus : null;
  const fieldPath = isObservation ? evidence.field_path : null;
  const reference = !isObservation ? evidence.reference : null;
  const source = reference ? readSourceReference(reference) : null;
  // Sin PDF fuente se muestra al menos el código de la regla citada.
  const referenceRuleCode = typeof reference?.rule_code === "string" ? reference.rule_code : null;

  return (
    <div
      role="dialog"
      aria-labelledby="evidence-dialog-title"
      className="bg-background border border-border rounded-lg p-5  space-y-3 text-sm"
    >
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border pb-4">
        <div className="flex min-w-0 flex-wrap items-center gap-2">
          <FileText aria-hidden="true" className="w-4 h-4 text-primary" />
          <h4 id="evidence-dialog-title" className="font-semibold text-foreground text-lg leading-7">
            {es.evidence.panelTitle} #{evidence.id}
          </h4>
          <Badge variant="outline">
            {isObservation ? es.evidence.observation : es.evidence.ruleSource}
          </Badge>
        </div>
        <Button
          type="button"
          variant="ghost"
          size="icon"
          onClick={onClose}
          className="size-10"
          title={es.evidence.close}
          aria-label={es.evidence.close}
        >
          <X aria-hidden="true" className="w-4 h-4" />
        </Button>
      </div>

      <div className="space-y-2 text-foreground">
        {fieldPath && (
          <div>
            <span className="text-sm font-semibold text-muted-foreground block mb-0.5">
              {es.evidence.fieldPath}
            </span>
            <code className="text-sm font-mono bg-muted px-1.5 py-0.5 rounded block">
              {fieldPath}
            </code>
          </div>
        )}

        {obs && (
          <>
            <div>
              <span className="text-sm font-semibold text-muted-foreground block mb-0.5">
                {es.evidence.extractedText}
              </span>
              <p className="p-2 bg-muted/40 border border-border rounded font-mono text-sm text-foreground">
                {obs.source_text ?? String(obs.normalized_value ?? obs.raw_value)}
              </p>
            </div>

            {obs.unit && (
              <div className="flex gap-2">
                <span className="text-sm text-muted-foreground">{es.evidence.unit}:</span>
                <span className="font-semibold">{obs.unit}</span>
              </div>
            )}
          </>
        )}

        {reference && (
          <div>
            <span className="text-sm font-semibold text-muted-foreground block mb-0.5">
              {es.evidence.ruleSource}
            </span>
            <p className="p-2 bg-muted/40 border border-border rounded text-sm text-foreground break-words">
              {source?.sourceText ?? referenceRuleCode ?? es.evidence.ruleSource}
            </p>
            {source && onOpenSource && (
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="mt-1.5 min-h-10 text-sm"
                onClick={() => onOpenSource(source, source.catalogCode ?? source.ruleCode ?? es.evidence.ruleSource)}
              >
                {source.page !== null ? es.tariffReference.showSourcePage(source.page) : es.tariffReference.showSource}
              </Button>
            )}
          </div>
        )}

        {focus?.page_number !== undefined && focus?.page_number !== null && (
          <div className="flex items-center justify-between pt-1">
            <span className="text-sm text-muted-foreground flex items-center gap-1">
              <MapPin aria-hidden="true" className="w-3.5 h-3.5 text-muted-foreground" />
              {es.evidence.pageNumber}: {focus.page_number}
              {focus.fallback && (
                <span className="text-sm text-muted-foreground">({focus.fallback})</span>
              )}
            </span>
            {onGoToPage && (
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => {
                  const targetPage = focus.page_number;
                  if (targetPage !== null && targetPage !== undefined) {
                    onGoToPage(targetPage);
                  }
                }}
                className="min-h-10 text-sm"
              >
                {es.evidence.goToPage(focus.page_number)}
              </Button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
