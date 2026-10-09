import { CalendarDays, ChevronLeft, ChevronRight } from "lucide-react";
import { Popover } from "radix-ui";
import { useRef, useState } from "react";
import { es } from "@/lib/i18n";
import { Button } from "./button";
import { dateValue, monthDays, parseDate } from "./date-picker-model";

interface DatePickerProps {
  id: string;
  label: string;
  value: string;
  min?: string;
  max?: string;
  onChange(value: string): void;
}

const locale = "es-MX";

export function DatePicker({ id, label, value, min, max, onChange }: DatePickerProps) {
  const [open, setOpen] = useState(false);
  const [month, setMonth] = useState(new Date());
  const [focused, setFocused] = useState("");
  const dayRefs = useRef(new Map<string, HTMLButtonElement>());
  const focusPending = useRef(false);
  const allowed = (day: string) => (!min || day >= min) && (!max || day <= max);
  const choose = (day: string) => { onChange(day); setOpen(false); };
  const moveMonth = (offset: number) => {
    const next = new Date(month.getFullYear(), month.getMonth() + offset, 1, 12);
    setMonth(next);
    const firstAllowed = monthDays(next).find((day) => day && allowed(dateValue(day)));
    setFocused(firstAllowed ? dateValue(firstAllowed) : "");
  };
  return <Popover.Root open={open} onOpenChange={(next) => {
    if (next) {
      const initial = value || (min && dateValue(new Date()) < min ? min : max && dateValue(new Date()) > max ? max : dateValue(new Date()));
      setMonth(parseDate(initial)); setFocused(initial);
    }
    setOpen(next);
  }}>
    <Popover.Trigger asChild>
      <Button id={id} type="button" variant="outline" className="h-11 w-full justify-between px-3 font-normal" aria-label={`${label}: ${value ? parseDate(value).toLocaleDateString(locale) : es.datePicker.placeholder}`}>
        <span className={value ? "tabular-nums" : "text-muted-foreground"}>{value ? parseDate(value).toLocaleDateString(locale, { day: "2-digit", month: "2-digit", year: "numeric" }) : es.datePicker.placeholder}</span>
        <CalendarDays aria-hidden="true" className="size-4 text-muted-foreground" />
      </Button>
    </Popover.Trigger>
    <Popover.Portal>
      <Popover.Content align="start" sideOffset={6} collisionPadding={16} aria-label={`${es.datePicker.calendar}: ${label}`}
        onOpenAutoFocus={(event) => { event.preventDefault(); dayRefs.current.get(focused)?.focus({ preventScroll: true }); }}
        className="z-50 w-[22rem] max-w-[calc(100vw-2rem)] max-h-[var(--radix-popover-content-available-height)] overflow-y-auto rounded-xl border border-border bg-popover p-3 text-popover-foreground">
        <div className="mb-3 flex items-center justify-between gap-2">
          <Button type="button" variant="ghost" className="size-11" aria-label={es.datePicker.previous} onClick={() => moveMonth(-1)}><ChevronLeft aria-hidden="true" /></Button>
          <span aria-live="polite" className="text-sm font-semibold capitalize">{month.toLocaleDateString(locale, { month: "long", year: "numeric" })}</span>
          <Button type="button" variant="ghost" className="size-11" aria-label={es.datePicker.next} onClick={() => moveMonth(1)}><ChevronRight aria-hidden="true" /></Button>
        </div>
        <div className="grid grid-cols-7 gap-1">
          {es.datePicker.weekdays.map((day) => <span key={day} className="py-2 text-center text-xs font-medium text-muted-foreground">{day}</span>)}
          {monthDays(month).map((date, index) => {
            if (!date) return <span key={`empty-${index}`} />;
            const day = dateValue(date);
            return <Button key={day} type="button" variant={day === value ? "default" : "ghost"}
              className={`h-11 w-full px-0 tabular-nums ${day === dateValue(new Date()) && day !== value ? "border-border" : ""}`}
              disabled={!allowed(day)} tabIndex={day === focused ? 0 : -1}
              aria-label={date.toLocaleDateString(locale, { weekday: "long", day: "numeric", month: "long", year: "numeric" })}
              aria-pressed={day === value} aria-current={day === dateValue(new Date()) ? "date" : undefined}
              ref={(node) => {
                if (node) { dayRefs.current.set(day, node); if (focusPending.current && day === focused) { node.focus({ preventScroll: true }); focusPending.current = false; } }
                else dayRefs.current.delete(day);
              }}
              onFocus={() => setFocused(day)} onClick={() => choose(day)}
              onKeyDown={(event) => {
                const offset = { ArrowLeft: -1, ArrowRight: 1, ArrowUp: -7, ArrowDown: 7 }[event.key];
                if (offset === undefined) return;
                event.preventDefault();
                const next = new Date(date.getFullYear(), date.getMonth(), date.getDate() + offset, 12);
                if (!allowed(dateValue(next))) return;
                focusPending.current = true; setFocused(dateValue(next)); setMonth(next);
              }}>{date.getDate()}</Button>;
          })}
        </div>
        <div className="mt-3 flex justify-between gap-2 border-t border-border pt-3">
          <Button type="button" variant="ghost" className="min-h-11" onClick={() => choose("")}>{es.datePicker.clear}</Button>
          <Button type="button" variant="outline" className="min-h-11" disabled={!allowed(dateValue(new Date()))} onClick={() => choose(dateValue(new Date()))}>{es.datePicker.today}</Button>
        </div>
      </Popover.Content>
    </Popover.Portal>
  </Popover.Root>;
}
