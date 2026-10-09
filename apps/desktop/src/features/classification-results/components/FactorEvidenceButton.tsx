import { DropdownMenu } from "radix-ui";
import { Button } from "@/components/ui/button";
import type { EvidenceLinkDto } from "@/lib/api";
import { es } from "@/lib/i18n";

export function FactorEvidenceButton({ links, onOpen }: {
  links: readonly EvidenceLinkDto[];
  onOpen: (id: number) => void;
}) {
  const destinations = new Map<string, EvidenceLinkDto>();
  for (const link of links) {
    const destination = link.source_type === "observation" && link.observation_id !== null
      ? `observation:${link.observation_id}` : link.detail_url;
    if (!destinations.has(destination)) destinations.set(destination, link);
  }
  const unique = [...destinations.values()];
  const first = unique[0];
  if (!first) return null;
  if (unique.length === 1) return <Button type="button" variant="outline" className="min-h-10" onClick={() => onOpen(first.id)}>{es.classification.evidenceLink}</Button>;
  const labels: Readonly<Record<string, string>> = es.workspace.factorFields;
  return <DropdownMenu.Root>
    <DropdownMenu.Trigger asChild>
      <Button type="button" variant="outline" className="min-h-10">{es.classification.evidenceLink}</Button>
    </DropdownMenu.Trigger>
    <DropdownMenu.Portal>
      <DropdownMenu.Content align="start" sideOffset={4} aria-label={es.evidence.panelTitle}
        className="z-50 max-h-72 max-w-[calc(100vw-2rem)] overflow-y-auto rounded-lg border bg-popover p-1 text-popover-foreground shadow-md">
        {unique.map((link) => <DropdownMenu.Item key={link.id} onSelect={() => onOpen(link.id)}
          className="cursor-pointer rounded px-3 py-2 text-sm outline-none data-[highlighted]:bg-accent data-[highlighted]:text-accent-foreground">
          {link.source_type === "rule_source" ? es.evidence.ruleSource : labels[link.field_path ?? ""] ?? link.field_path?.replaceAll("_", " ") ?? `${es.evidence.observation} ${link.id}`}
        </DropdownMenu.Item>)}
      </DropdownMenu.Content>
    </DropdownMenu.Portal>
  </DropdownMenu.Root>;
}
