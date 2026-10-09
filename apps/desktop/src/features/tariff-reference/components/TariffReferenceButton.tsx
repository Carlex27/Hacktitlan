import { BookOpenIcon } from "lucide-react";

import { es } from "@/lib/i18n";

import { toLigieLookupCode } from "../model/ligieCode";

export interface TariffReferenceButtonProps {
  fraction: string | null;
  nico: string | null;
  /** Código como se muestra al usuario. */
  displayCode: string;
  onOpen(code: string, label: string): void;
}

/** Abre la página de la LIGIE del código; sin fracción no se muestra. */
export function TariffReferenceButton({ fraction, nico, displayCode, onOpen }: TariffReferenceButtonProps) {
  const code = toLigieLookupCode(fraction, nico);
  if (code === null) return null;

  return (
    <button
      type="button"
      aria-label={es.tariffReference.showInLigie(displayCode)}
      title={es.tariffReference.showInLigie(displayCode)}
      onClick={(event) => {
        // Dentro de una etiqueta de opción no debe cambiar la selección.
        event.preventDefault();
        event.stopPropagation();
        onOpen(code, displayCode);
      }}
      className="inline-flex shrink-0 items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-medium text-blue-700 hover:bg-blue-50 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
    >
      <BookOpenIcon aria-hidden="true" className="size-3" />
      {es.tariffReference.showInLigieShort}
    </button>
  );
}
