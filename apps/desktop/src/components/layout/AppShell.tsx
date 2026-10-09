import type { ComponentType, ReactNode } from "react";
import { FileCheck } from "lucide-react";
import { Button } from "@/components/ui/button";

import { es } from "@/lib/i18n";
import { cn } from "@/lib/utils";

export interface NavItem {
  id: string;
  label: string;
  icon: ComponentType<{ className?: string; "aria-hidden"?: boolean | "true" | "false" }>;
  disabled?: boolean;
}

export interface BreadcrumbItem {
  label: string;
  onClick?: () => void;
}

export interface AppShellProps {
  items: readonly NavItem[];
  activeId: string;
  onNavigate(id: string): void;
  breadcrumbs: readonly BreadcrumbItem[];
  children: ReactNode;
}

export function AppShell({
  items,
  activeId,
  onNavigate,
  breadcrumbs,
  children,
}: AppShellProps) {
  return (
    <div className="fixed inset-0 flex flex-col h-dvh w-full overflow-clip bg-app-canvas font-sans text-slate-800 text-[13px] antialiased">
      <header className="shrink-0 overflow-y-auto [scrollbar-gutter:stable] border-b border-sidebar-border bg-sidebar text-sidebar-foreground px-4 py-3 sm:px-8">
        <div className="mx-auto flex w-full max-w-6xl min-w-0 flex-wrap items-center gap-3 sm:gap-x-8">
          <div
            className="flex min-h-10 shrink-0 items-center gap-3"
            title={es.app.title}
          >
            <span className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-sidebar-primary text-sidebar-primary-foreground">
              <FileCheck aria-hidden="true" className="size-5" />
            </span>
            <span className="text-sm leading-5 font-semibold">{es.app.title}</span>
          </div>

          <nav className="grid min-w-0 grid-cols-2 gap-2 sm:flex sm:items-center" aria-label={es.nav.label}>
            {items.map((item) => {
              const Icon = item.icon;
              const isActive = item.id === activeId;

              return (
                <Button
                  key={item.id}
                  type="button"
                  variant="ghost"
                  disabled={item.disabled}
                  aria-current={isActive ? "page" : undefined}
                  onClick={() => onNavigate(item.id)}
                  title={item.disabled ? `${item.label} (${es.nav.comingSoon})` : item.label}
                  className={cn(
                    "h-auto min-h-11 min-w-0 gap-2 whitespace-normal px-3 py-2 text-sm leading-5 focus-visible:ring-0 focus-visible:outline-2 focus-visible:outline-sidebar-primary focus-visible:outline-offset-2",
                    isActive
                      ? "bg-sidebar-primary text-sidebar-primary-foreground font-semibold hover:bg-sidebar-primary hover:text-sidebar-primary-foreground"
                      : "text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
                  )}
                >
                  <Icon aria-hidden="true" className="size-5 shrink-0" />
                  <span className="text-center">{item.label}</span>
                </Button>
              );
            })}
          </nav>
          {breadcrumbs.length > 0 && <nav aria-label="Migas de pan" className="flex min-w-0 basis-full items-center gap-2 text-sm text-muted-foreground xl:ml-auto xl:basis-auto xl:flex-1 xl:justify-end">
            {breadcrumbs.map((crumb, idx) => {
              const isLast = idx === breadcrumbs.length - 1;
              return (
                <div key={crumb.label} className={cn("flex min-w-0 items-center gap-2", !isLast && "shrink-0")}>
                  {idx > 0 && <span aria-hidden="true" className="text-muted-foreground">/</span>}
                  {isLast ? (
                    <span className="break-all font-semibold text-sidebar-foreground" aria-current="page">
                      {crumb.label}
                    </span>
                  ) : crumb.onClick ? (
                    <Button
                      type="button"
                      variant="ghost"
                      onClick={crumb.onClick}
                      className="min-h-11 whitespace-normal px-2 text-muted-foreground hover:underline"
                    >
                      {crumb.label}
                    </Button>
                  ) : (
                    <span>{crumb.label}</span>
                  )}
                </div>
              );
            })}
          </nav>}
        </div>
      </header>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 min-h-0 overflow-hidden">
        {/* Content Slot */}
        <div className="flex-1 flex overflow-hidden min-h-0">{children}</div>
      </div>
    </div>
  );
}
