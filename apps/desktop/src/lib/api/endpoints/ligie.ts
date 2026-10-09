import type { ApiClient, RequestOptions } from "../client";
import type { LigieEntriesMetaDto, LigieEntryDto } from "../dto";

export interface LigieEntriesResponse {
  /** Puede haber varias: la fuente tiene códigos duplicados que no se resuelven. */
  entries: readonly LigieEntryDto[];
  meta: LigieEntriesMetaDto;
}

/**
 * Busca una fracción o NICO en la LIGIE fuente. Acepta `7208.51.01-00`,
 * `7208510100` o sólo la fracción.
 */
export async function getLigieEntries(
  api: ApiClient,
  code: string,
  options?: RequestOptions,
): Promise<LigieEntriesResponse> {
  const envelope = await api.get<LigieEntryDto[]>(
    `/api/v1/rule-sources/ligie-72/entries/${encodeURIComponent(code)}`,
    options,
  );
  return { entries: envelope.data, meta: envelope.meta as unknown as LigieEntriesMetaDto };
}
