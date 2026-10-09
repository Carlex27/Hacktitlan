import { ArrowRight } from "lucide-react";
import { cn } from "@/lib/utils";
import { useGuideSection } from "./useGuideSection";
import { GuideStep } from "./GuideStep";
import { es } from "@/lib/i18n";

export function ClassificationGuide() {
  const text = es.classificationGuide;
  const { ref, activeId, setActiveId } = useGuideSection();
  return <div ref={ref} className="grid items-start gap-8 lg:grid-cols-[minmax(0,1fr)_15rem] lg:gap-16">
    <aside className="rounded-lg bg-muted/60 p-5 lg:sticky lg:top-8 lg:col-start-2 lg:row-start-1">
      <nav aria-label={text.contents}>
        <h3 className="mb-3 text-sm font-semibold">{text.contents}</h3>
        <div className="flex flex-wrap gap-x-4 lg:flex-col lg:gap-0">
          {text.sectionLinks.map((link) => <a key={link.id} href={`#${link.id}`} aria-current={activeId === link.id ? "location" : undefined} onClick={() => setActiveId(link.id)}
            className={cn("flex min-h-11 items-center gap-2 rounded-md px-2 text-sm leading-5 text-foreground underline-offset-4 hover:bg-accent focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary", activeId === link.id && "bg-background font-semibold")}>
            <ArrowRight aria-hidden="true" className={cn("size-4 shrink-0", activeId !== link.id && "invisible")} />
            {link.label}</a>)}
        </div>
      </nav>
      <details className="mt-4 border-t border-border pt-3">
        <summary className="min-h-11 cursor-pointer rounded-sm py-3 text-sm font-semibold focus-visible:outline-2 focus-visible:outline-primary">{text.scopeTitle}</summary>
        <p className="text-sm leading-6 text-muted-foreground">{text.scope}</p>
      </details>
    </aside>
    <article className="min-w-0 space-y-10 text-base leading-7 lg:col-start-1 lg:row-start-1">
    <section aria-labelledby="app-help">
      <h3 id="app-help" tabIndex={-1} className="scroll-mt-8 text-xl leading-7 font-semibold focus-visible:outline-2 focus-visible:outline-primary">{text.helpTitle}</h3>
      <p className="mt-2 mb-3 text-sm leading-6 text-muted-foreground">{text.helpHint}</p>
      <ol>{text.helpAreas.map((area, index) => <GuideStep key={area.title} number={index + 1} {...area} />)}</ol>
    </section>
    <section aria-labelledby="classification-flow" className="border-t border-border pt-8">
      <h3 id="classification-flow" tabIndex={-1} className="scroll-mt-8 text-xl leading-7 font-semibold focus-visible:outline-2 focus-visible:outline-primary">{text.flowTitle}</h3>
      <p className="mt-2 mb-3 text-sm leading-6 text-muted-foreground">{text.flowHint}</p>
      <ol>{text.steps.map((step, index) => <GuideStep key={step.title} number={index + 1} {...step} />)}</ol>
    </section>
    <section aria-labelledby="classification-reading" className="border-t border-border pt-8">
      <h3 id="classification-reading" tabIndex={-1} className="scroll-mt-8 focus-visible:outline-2 focus-visible:outline-primary mb-5 text-xl leading-7 font-semibold">{text.readingTitle}</h3>
      <dl className="space-y-5">{text.meanings.map((meaning) => <div key={meaning.title}>
        <dt className="font-semibold">{meaning.title}</dt><dd className="mt-1 text-muted-foreground">{meaning.body}</dd>
      </div>)}</dl>
    </section>
    <section aria-labelledby="classification-example" className="rounded-lg border border-warning-border bg-warning-background p-5 text-warning-foreground">
      <h3 id="classification-example" tabIndex={-1} className="scroll-mt-8 focus-visible:outline-2 focus-visible:outline-primary text-lg leading-7 font-semibold">{text.exampleTitle}</h3><p className="mt-2">{text.example}</p>
    </section>
    <section aria-labelledby="classification-review">
      <h3 id="classification-review" tabIndex={-1} className="scroll-mt-8 focus-visible:outline-2 focus-visible:outline-primary mb-4 text-xl leading-7 font-semibold">{text.reviewTitle}</h3>
      <div className="space-y-4 text-muted-foreground">{text.review.map((paragraph) => <p key={paragraph}>{paragraph}</p>)}</div>
    </section>
    <section aria-labelledby="classification-trace" className="border-t border-border pt-8">
      <h3 id="classification-trace" tabIndex={-1} className="scroll-mt-8 focus-visible:outline-2 focus-visible:outline-primary mb-3 text-xl leading-7 font-semibold">{text.traceTitle}</h3><p className="text-muted-foreground">{text.trace}</p>
    </section>
  </article>
  </div>;
}
