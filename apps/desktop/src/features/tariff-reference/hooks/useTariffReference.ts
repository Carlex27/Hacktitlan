import { useCallback, useState } from "react";

import type { SourceReference } from "@/features/classification-results";

export interface OpenTariffReference {
  /** Código como se mostró al usuario (p. ej. `7208.51.01.00`). */
  label: string;
  reference: SourceReference;
}

export interface TariffReference {
  /** Referencia abierta; `null` si aún no se consulta ninguna. */
  active: OpenTariffReference | null;
  open(reference: SourceReference, label: string): void;
}

/** Referencia de la fuente normativa abierta en el visor (sin llamadas extra al API). */
export function useTariffReference(): TariffReference {
  const [active, setActive] = useState<OpenTariffReference | null>(null);
  const open = useCallback((reference: SourceReference, label: string) => {
    setActive({ reference, label });
  }, []);
  return { active, open };
}
