import type { CertificateObservationDto } from "@/lib/api";
import { es } from "@/lib/i18n";
import { displayObservationValue as display, primaryObservations, verifiedChemicalObservations } from "../model";

export function ExtractedObservations({ observations, products = [] }: {
  observations: readonly CertificateObservationDto[];
  products?: readonly { id: number; product_identifier: string | null }[];
}) {
  const text = es.workspace;
  const rows = [...primaryObservations(observations), ...verifiedChemicalObservations(observations)];
  return <section aria-label={text.extracted} className="rounded-xl border border-border bg-background p-4">
    <details><summary className="min-h-10 cursor-pointer py-2 text-base leading-6 font-semibold focus-visible:outline-2 focus-visible:outline-primary">{text.extracted}</summary>
    <div className="mt-4">
    {!rows.length ? <p className="text-sm text-muted-foreground">{text.noPrimaryObservations}</p> : <div className="overflow-x-auto focus-visible:outline-2 focus-visible:outline-primary" tabIndex={0} role="region" aria-label={text.extracted}>
      <table className="w-full min-w-[40rem] text-left text-sm leading-6"><thead className="bg-muted/40 text-muted-foreground"><tr>{[text.field, text.raw, text.normalized].map((label) =>
        <th key={label} scope="col" className="border-b p-3 font-medium">{label}</th>)}</tr></thead>
        <tbody>{rows.map((value) => <tr key={value.id} className="border-b last:border-0">
          <th scope="row" className="p-2 align-middle font-medium">{value.label}
            {value.product_id !== null && <p className="font-normal text-muted-foreground">{es.verification.series}: {products.find((product) => product.id === value.product_id)?.product_identifier ?? `#${value.product_id}`}</p>}</th>
          <td className="max-w-72 break-words p-2 align-middle">{display(value.raw_value)}</td>
          <td className="max-w-72 break-words p-2 align-middle">{display(value.normalized_value)} {value.normalized_value !== null && value.unit}</td>
        </tr>)}</tbody></table>
    </div>}
    </div></details>
  </section>;
}
