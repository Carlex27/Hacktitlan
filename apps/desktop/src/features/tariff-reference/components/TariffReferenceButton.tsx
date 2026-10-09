import { BookOpenIcon } from "lucide-react";
import { Button } from "@/components/ui/button";

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
    <Button
      type="button"
      variant="outline"
      aria-label={es.tariffReference.showInLigie(displayCode)}
      title={es.tariffReference.showInLigie(displayCode)}
      onClick={(event) => {
        // Dentro de una etiqueta de opción no debe cambiar la selección.
        event.preventDefault();
        event.stopPropagation();
        onOpen(reference, displayCode);
      }}
      className="min-h-10 text-sm"
    >
      <BookOpenIcon aria-hidden="true" className="size-3" />
      {es.tariffReference.showInLigieShort}
    </Button>
  );
}
