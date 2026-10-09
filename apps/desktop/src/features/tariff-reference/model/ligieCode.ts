/**
 * Código para consultar la LIGIE a partir de fracción y NICO tal como llegan del
 * backend (con o sin puntos). Sin fracción no hay referencia que buscar.
 */
export function toLigieLookupCode(fraction: string | null, nico: string | null): string | null {
  const fractionDigits = fraction?.replace(/\D/g, "") ?? "";
  if (fractionDigits.length === 0) return null;
  const nicoDigits = nico?.replace(/\D/g, "") ?? "";
  return `${fractionDigits}${nicoDigits}`;
}
