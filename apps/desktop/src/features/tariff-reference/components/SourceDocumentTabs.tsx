import type { ReactNode } from "react";

import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { es } from "@/lib/i18n";

import type { TariffReferenceState } from "../hooks/useTariffReference";

export type SourceDocumentTab = "acta" | "ligie";

export interface SourceDocumentTabsProps {
  activeTab: SourceDocumentTab;
  onTabChange(tab: SourceDocumentTab): void;
  referenceState: TariffReferenceState;
  /** Visor del acta; se recibe como slot para no acoplar features. */
  actaViewer: ReactNode;
  ligieViewer: ReactNode;
}

function ligieTabLabel(state: TariffReferenceState): string {
  if (state.status !== "success") return es.tariffReference.ligieTab;
  const page = state.entries[state.activeIndex]?.page ?? null;
  return page === null ? es.tariffReference.ligieTab : es.tariffReference.ligieTabPage(page);
}

/** Pestañas del panel izquierdo: el acta y la LIGIE como referencia de NICO. */
export function SourceDocumentTabs({
  activeTab,
  onTabChange,
  referenceState,
  actaViewer,
  ligieViewer,
}: SourceDocumentTabsProps) {
  return (
    <Tabs
      value={activeTab}
      onValueChange={(value) => onTabChange(value === "ligie" ? "ligie" : "acta")}
      className="flex h-full min-h-0 flex-col gap-0"
    >
      <TabsList
        aria-label={es.tariffReference.viewerTabs}
        className="h-9 w-full shrink-0 justify-start rounded-none bg-viewer-header px-2"
      >
        <TabsTrigger value="acta" className="flex-none text-xs text-slate-300 data-[state=active]:text-slate-900">
          {es.tariffReference.actaTab}
        </TabsTrigger>
        <TabsTrigger value="ligie" className="flex-none text-xs text-slate-300 data-[state=active]:text-slate-900">
          {ligieTabLabel(referenceState)}
        </TabsTrigger>
      </TabsList>
      {/* forceMount conserva el PDF del acta cargado al cambiar de pestaña. */}
      <TabsContent value="acta" forceMount className="min-h-0 flex-1 data-[state=inactive]:hidden">
        {actaViewer}
      </TabsContent>
      <TabsContent value="ligie" forceMount className="min-h-0 flex-1 data-[state=inactive]:hidden">
        {ligieViewer}
      </TabsContent>
    </Tabs>
  );
}
