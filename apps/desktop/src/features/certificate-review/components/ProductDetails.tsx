import type { CertificateHeatDto, CertificateProductDto } from "@/lib/api";
import { es } from "@/lib/i18n";

export function ProductDetails({ product, heat }: { product: CertificateProductDto; heat: CertificateHeatDto | undefined }) {
  const text = es.workspace;
  const terms: Readonly<Record<string, string>> = text.terms;
  const fields = [
    [text.serial, product.product_identifier], [text.labelNo, product.label_no],
    [text.form, terms[product.form ?? ""] ?? product.form], [text.rolling, terms[product.rolling ?? ""] ?? product.rolling], [text.weight, product.weight_kg],
    [text.coiled, product.coiled === null ? null : product.coiled ? text.inCoils : text.notCoiled],
    [text.grade, heat?.grade], [text.standard, heat?.standard],
  ];
  return <dl className="grid gap-x-8 gap-y-5 border-b border-border pb-6 sm:grid-cols-2 xl:grid-cols-4">
    {fields.map(([label, value]) => <div key={label}><dt className="text-sm text-muted-foreground">{label}</dt>
      <dd className="mt-1 break-words text-sm font-medium">{value ?? text.unknown}</dd></div>)}
  </dl>;
}
