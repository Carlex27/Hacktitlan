import { ClassificationGuide } from "@/features/classification-guide";
import { es } from "@/lib/i18n";

export function ClassificationGuidePage() {
  return <main className="min-h-0 min-w-0 flex-1 overflow-y-auto bg-background px-4 py-8 text-foreground sm:px-8">
    <div className="mx-auto max-w-6xl space-y-8">
      <header className="space-y-3 border-b border-border pb-7">
        <h2 className="text-3xl leading-10 font-semibold tracking-tight">{es.classificationGuide.title}</h2>
        <p className="max-w-3xl text-base leading-7 text-muted-foreground">{es.classificationGuide.introduction}</p>
      </header>
      <ClassificationGuide />
    </div>
  </main>;
}
