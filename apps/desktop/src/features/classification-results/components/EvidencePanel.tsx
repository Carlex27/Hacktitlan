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
      className="bg-white border border-slate-300 rounded-lg p-3.5 shadow-md space-y-3 text-xs"
    >
      <div className="flex items-center justify-between border-b border-slate-100 pb-2">
        <div className="flex items-center gap-2">
          <FileText aria-hidden="true" className="w-4 h-4 text-blue-600" />
          <h4 id="evidence-dialog-title" className="font-bold text-slate-900 text-xs">
            {es.evidence.panelTitle} #{evidence.id}
          </h4>
          <Badge variant="outline">
            {isObservation ? es.evidence.observation : es.evidence.ruleSource}
          </Badge>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="p-1 text-slate-400 hover:text-slate-700 rounded"
          title={es.evidence.close}
        >
          <X aria-hidden="true" className="w-4 h-4" />
        </button>
      </div>

      <div className="space-y-2 text-slate-700">
        {fieldPath && (
          <div>
            <span className="text-[10.5px] font-semibold text-slate-500 block mb-0.5">
              {es.evidence.fieldPath}
            </span>
            <code className="text-[11px] font-mono bg-slate-100 px-1.5 py-0.5 rounded block">
              {fieldPath}
            </code>
          </div>
        )}

        {obs && (
          <>
            <div>
              <span className="text-[10.5px] font-semibold text-slate-500 block mb-0.5">
                {es.evidence.extractedText}
              </span>
              <p className="p-2 bg-slate-50 border border-slate-200 rounded font-mono text-[11px] text-slate-900">
                {obs.source_text ?? String(obs.normalized_value ?? obs.raw_value)}
              </p>
            </div>

            {obs.unit && (
              <div className="flex gap-2">
                <span className="text-[10.5px] text-slate-500">Unidad:</span>
                <span className="font-semibold">{obs.unit}</span>
              </div>
            )}
          </>
        )}

        {reference && (
          <div>
            <span className="text-[10.5px] font-semibold text-slate-500 block mb-0.5">
              {es.evidence.ruleSource}
            </span>
            <p className="p-2 bg-slate-50 border border-slate-200 rounded text-[11px] text-slate-800 break-words">
              {source?.sourceText ?? referenceRuleCode ?? es.evidence.ruleSource}
            </p>
            {source && onOpenSource && (
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="mt-1.5 h-7 text-xs"
                onClick={() => onOpenSource(source, source.catalogCode ?? source.ruleCode ?? es.evidence.ruleSource)}
              >
                {source.page !== null ? es.tariffReference.showSourcePage(source.page) : es.tariffReference.showSource}
              </Button>
            )}
          </div>
        )}

        {focus?.page_number !== undefined && focus?.page_number !== null && (
          <div className="flex items-center justify-between pt-1">
            <span className="text-[11px] text-slate-600 flex items-center gap-1">
              <MapPin aria-hidden="true" className="w-3.5 h-3.5 text-slate-400" />
              {es.evidence.pageNumber}: {focus.page_number}
              {focus.fallback && (
                <span className="text-[10px] text-slate-400">({focus.fallback})</span>
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
                className="h-7 text-xs"
              >
                Ir a la página {focus.page_number}
              </Button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
