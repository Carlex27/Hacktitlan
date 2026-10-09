import { BookOpenIcon } from "lucide-react";

import type { SourceReference } from "@/features/classification-results";
import { es } from "@/lib/i18n";

export interface TariffReferenceButtonProps {
  /** Referencia que adjunta el backend; sin ella no hay a dónde ir y no se muestra. */
  reference: SourceReference | null;
  /** Código como se muestra al usuario. */
  displayCode: string;
  onOpen(reference: SourceReference, label: string): void;
}

export function TariffReferenceButton({ reference, displayCode, onOpen }: TariffReferenceButtonProps) {
  if (reference === null) return null;

  return (
    <button
      type="button"
      aria-label={es.tariffReference.showInLigie(displayCode)}
      title={es.tariffReference.showInLigie(displayCode)}
      onClick={(event) => {
        // Dentro de una etiqueta de opción no debe cambiar la selección.
        event.preventDefault();
        event.stopPropagation();
        onOpen(reference, displayCode);
      }}
      className="inline-flex shrink-0 items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-medium text-blue-700 hover:bg-blue-50 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
    >
      <BookOpenIcon aria-hidden="true" className="size-3" />
      {es.tariffReference.showInLigieShort}
    </button>
  );
}
