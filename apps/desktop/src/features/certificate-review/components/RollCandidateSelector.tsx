import { Check, ChevronDown } from "lucide-react";
import { DropdownMenu } from "radix-ui";
import { useRef } from "react";
import { Button } from "@/components/ui/button";
import { es } from "@/lib/i18n";

interface RollCandidate {
  id: number;
  fraction: string;
  nico: string;
  description: string | null;
  support_level: keyof typeof es.classification.supportLevel;
}

interface RollCandidateSelectorProps {
  candidates: readonly RollCandidate[];
  current: RollCandidate;
  identifier: string;
  disabled: boolean;
  onSelect(id: number): void;
}

export function RollCandidateSelector({ candidates, current, identifier, disabled, onSelect }: RollCandidateSelectorProps) {
  const label = `${es.workspace.nico}: ${identifier}`;
  const pendingCandidate = useRef<number | null>(null);
  return <DropdownMenu.Root>
    <DropdownMenu.Trigger asChild>
      <Button variant="outline" disabled={disabled} aria-label={label} className="min-h-11 gap-3 px-3 font-normal">
        <span className="tabular-nums font-medium">{current.fraction}</span>
        <span className="text-muted-foreground">NICO <span className="font-semibold text-foreground">{current.nico}</span></span>
        <ChevronDown aria-hidden="true" className="size-4 text-muted-foreground" />
      </Button>
    </DropdownMenu.Trigger>
    <DropdownMenu.Portal>
      <DropdownMenu.Content align="start" sideOffset={8} collisionPadding={16} aria-label={label}
        onCloseAutoFocus={(event) => {
          const candidateId = pendingCandidate.current;
          if (candidateId === null) return;
          event.preventDefault();
          pendingCandidate.current = null;
          onSelect(candidateId);
        }}
        className="z-50 w-[28rem] max-w-[calc(100vw-2rem)] max-h-[min(24rem,var(--radix-dropdown-menu-content-available-height))] overflow-y-auto rounded-xl bg-popover p-1.5 text-popover-foreground shadow-md ring-1 ring-border">
        <DropdownMenu.RadioGroup value={String(current.id)}>
          {candidates.map((candidate) => <DropdownMenu.RadioItem key={candidate.id} value={String(candidate.id)}
            onSelect={() => { pendingCandidate.current = candidate.id; }}
            className="relative cursor-pointer rounded-lg py-3 pl-9 pr-3 outline-none data-[highlighted]:bg-accent data-[highlighted]:text-accent-foreground focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-primary">
            <DropdownMenu.ItemIndicator className="absolute left-3 top-4"><Check aria-hidden="true" className="size-4" /></DropdownMenu.ItemIndicator>
            <span className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm leading-5">
              <span className="font-semibold tabular-nums">{candidate.fraction}</span>
              <span className="rounded-md bg-muted px-2 py-0.5 font-medium tabular-nums">NICO {candidate.nico}</span>
            </span>
            <span className="mt-2 block whitespace-normal break-words text-sm leading-6 text-muted-foreground">
              {candidate.description ?? es.classification.supportLevel[candidate.support_level]}
            </span>
          </DropdownMenu.RadioItem>)}
        </DropdownMenu.RadioGroup>
      </DropdownMenu.Content>
    </DropdownMenu.Portal>
  </DropdownMenu.Root>;
}
