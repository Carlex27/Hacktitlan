import { Check, ChevronDown } from "lucide-react";
import { Select } from "radix-ui";

export interface SelectFieldProps {
  id: string;
  disabled?: boolean;
  value: string;
  options: readonly { value: string; label: string }[];
  onChange(value: string): void;
}

export function SelectField({ id, value, options, onChange, disabled = false }: SelectFieldProps) {
  return <Select.Root disabled={disabled} value={value} onValueChange={onChange}>
    <Select.Trigger id={id} className="flex h-11 w-full items-center justify-between gap-3 rounded-lg border border-input bg-background px-3 text-sm text-foreground outline-none focus-visible:ring-3 focus-visible:ring-ring/50 disabled:cursor-not-allowed disabled:opacity-50">
      <Select.Value /><Select.Icon><ChevronDown aria-hidden="true" className="size-4 text-muted-foreground" /></Select.Icon>
    </Select.Trigger>
    <Select.Portal>
      <Select.Content position="popper" align="start" sideOffset={6} collisionPadding={16}
        className="z-50 min-w-[var(--radix-select-trigger-width)] max-h-[var(--radix-select-content-available-height)] overflow-y-auto rounded-xl border border-border bg-popover p-1.5 text-popover-foreground">
        <Select.Viewport>
          {options.map((option) => <Select.Item key={option.value} value={option.value}
            className="relative flex min-h-11 cursor-pointer items-center rounded-lg py-2 pl-9 pr-3 text-sm outline-none data-[highlighted]:bg-accent data-[highlighted]:text-accent-foreground">
            <Select.ItemIndicator className="absolute left-3"><Check aria-hidden="true" className="size-4" /></Select.ItemIndicator>
            <Select.ItemText>{option.label}</Select.ItemText>
          </Select.Item>)}
        </Select.Viewport>
      </Select.Content>
    </Select.Portal>
  </Select.Root>;
}
