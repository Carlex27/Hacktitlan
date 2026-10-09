/** Fuente LIGIE capítulo 72: referencia visual de fracciones y NICO. */

export type LigieEntryKindDto =
  | "nico"
  | "fraction"
  | "subheading"
  | "heading"
  | "qualifier"
  | "section";

/** Elemento de `GET /api/v1/rule-sources/ligie-72/entries/{code}`. */
export interface LigieEntryDto {
  /** Código tal como aparece en la fuente, p. ej. `7208.51.01-00`. */
  code: string;
  kind: LigieEntryKindDto;
  description: string;
  /** Página del PDF fuente; `null` si la extracción no la registró. */
  page: number | null;
  fraction: string | null;
  nico: string | null;
  umt: string | null;
  import_tax: string | null;
  export_tax: string | null;
}

export interface LigieFileStatusDto {
  available: boolean;
  code: string | null;
  message: string | null;
}

/** `meta` de la consulta de entradas. */
export interface LigieEntriesMetaDto {
  source: string;
  catalog_sha256: string;
  /** Ruta relativa del PDF; resolver con `ApiClient.url()`. */
  file_url: string;
  file_status: LigieFileStatusDto;
  /** Advertencia jurídica de la fuente, redactada por el backend. */
  notice: string;
}
