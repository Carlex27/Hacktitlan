import type { FormatTestDto, JsonObject, JsonValue } from "@/lib/api";

function record(value: JsonValue | undefined): JsonObject | null {
  return value !== null && typeof value === "object" && !Array.isArray(value) ? value as JsonObject : null;
}
export interface PreviewRow { product: string | null; field: string; original: JsonValue; normalized: JsonValue; page: number | null }
export function previewRows(result: NonNullable<FormatTestDto["result"]>): PreviewRow[] {
  const products = result.certificate?.products;
  if (!Array.isArray(products)) return [];
  return products.flatMap(item => {
    const product = record(item); if (!product) return [];
    const identifier = typeof product.product_id === "string" ? product.product_id : null;
    const evidence = result.evidence.filter(e => (!e.product_id || e.product_id === identifier) && (!e.heat_no || e.heat_no === product.heat_no));
    const fields = evidence.length ? evidence : Object.entries(product).filter(([, value]) => value !== null && typeof value !== "object").map(([field]) => ({ field }));
    return fields.map(e => {
      const field = typeof e.field === "string" ? e.field : "";
      const chemistry = field.startsWith("chemistry.") ? record(product.composition_pct)?.[field.slice(10)] : undefined;
      const metadata = record(result.certificate?.document)?.[field];
      const normalized = chemistry ?? product[field === "length_raw" ? "length_m" : field] ?? record(product.mechanical_properties)?.[field] ?? metadata ?? null;
      return { product: identifier, field, original: "raw_value" in e ? e.raw_value ?? null : null,
        normalized, page: "page_number" in e && typeof e.page_number === "number" ? e.page_number : null };
    });
  });
}
