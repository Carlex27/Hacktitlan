import { ChevronDown } from "lucide-react";

interface GuideStepProps {
  number: number;
  title: string;
  preview: string;
  body: string;
}

export function GuideStep({ number, title, preview, body }: GuideStepProps) {
  return <li className="border-b border-border last:border-b-0">
    <details className="group">
      <summary className="flex min-h-11 cursor-pointer list-none items-start gap-3 rounded-md py-5 focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-primary [&::-webkit-details-marker]:hidden sm:gap-4">
        <span aria-hidden="true" className="flex size-9 shrink-0 items-center justify-center rounded-full border border-border bg-background text-sm font-semibold tabular-nums group-open:border-primary group-open:bg-primary group-open:text-primary-foreground">{number}</span>
        <span className="min-w-0 flex-1"><span className="block font-semibold group-hover:underline underline-offset-4">{title}</span>
          <span className="mt-1 block text-sm leading-6 text-muted-foreground">{preview}</span>
        </span>
        <ChevronDown aria-hidden="true" className="mt-2 size-4 shrink-0 text-muted-foreground group-open:rotate-180" />
      </summary>
      <p className="pb-6 pl-12 text-base leading-7 text-foreground sm:pl-13">{body}</p>
    </details>
  </li>;
}
