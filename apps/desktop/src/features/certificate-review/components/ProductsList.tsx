import { Layers } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Empty, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from "@/components/ui/empty";
import { Skeleton } from "@/components/ui/skeleton";
import type { CertificateProductDto } from "@/lib/api";
import { es } from "@/lib/i18n";

export interface ProductsListProps {
  products: readonly CertificateProductDto[];
  isLoading?: boolean;
}

export function ProductsList({ products, isLoading = false }: ProductsListProps) {
  if (isLoading) {
    return (
      <div className="bg-white p-3 rounded-lg border border-slate-200 shadow-sm space-y-2">
        <Skeleton className="h-4 w-40" />
        <Skeleton className="h-12 w-full" />
      </div>
    );
  }

  if (products.length === 0) {
    return (
      <section
        className="bg-white p-3 rounded-lg border border-slate-200 shadow-sm"
        aria-labelledby="products-title"
      >
        <h4 id="products-title" className="font-bold text-slate-800 text-xs mb-2">
          {es.certificateReview.products.title}
        </h4>
        <Empty className="py-3">
          <EmptyHeader>
            <EmptyMedia variant="icon">
              <Layers aria-hidden="true" className="w-5 h-5 text-slate-400" />
            </EmptyMedia>
            <EmptyTitle className="text-xs">{es.certificateReview.products.emptyTitle}</EmptyTitle>
            <EmptyDescription className="text-[11px]">
              {es.certificateReview.products.emptyDescription}
            </EmptyDescription>
          </EmptyHeader>
        </Empty>
      </section>
    );
  }

  return (
    <section
      className="bg-white p-3 rounded-lg border border-slate-200 shadow-sm"
      aria-labelledby="products-title"
    >
      <div className="flex items-center justify-between mb-2">
        <h4 id="products-title" className="font-bold text-slate-800 text-xs">
          {es.certificateReview.products.title}
        </h4>
        <span className="text-[10px] text-slate-500 font-medium">
          {products.length} {products.length === 1 ? "partida" : "partidas"}
        </span>
      </div>

      <div className="space-y-2 max-h-48 overflow-y-auto">
        {products.map((p) => {
          const dims = [
            p.thickness_mm ? `Espesor: ${p.thickness_mm} mm` : null,
            p.width_mm ? `Ancho: ${p.width_mm} mm` : null,
            p.weight_kg ? `Peso: ${p.weight_kg} kg` : null,
          ]
            .filter(Boolean)
            .join(" · ");

          return (
            <div
              key={p.id}
              className="bg-slate-50/70 border border-slate-200 rounded p-2 text-xs flex items-center justify-between gap-2"
            >
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-slate-900 truncate">
                    {p.product_identifier ?? p.label_no ?? `Producto #${p.id}`}
                  </span>
                  {p.product_type && <Badge variant="outline">{p.product_type}</Badge>}
                  {p.coiled !== null && (
                    <span className="text-[10px] text-slate-500">
                      {p.coiled ? "En rollo" : "Sin enrollar"}
                    </span>
                  )}
                </div>
                <p className="text-[11px] text-slate-600 mt-0.5 truncate">
                  {dims || "Dimensiones no especificadas"}
                </p>
              </div>

              {p.rolling && (
                <span className="text-[10px] font-mono text-slate-500 shrink-0 uppercase">
                  {p.rolling}
                </span>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}
