import type { ComponentType, ReactNode } from "react";
import { ArrowLeft, FileCheck } from "lucide-react";
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
  const canGoBack = breadcrumbs.length > 1;

  return (
    <div className="fixed inset-0 flex h-dvh w-full overflow-clip bg-app-canvas font-sans text-slate-800 text-[13px] antialiased">
      {/* Left Sidebar */}
      <aside className="w-20 lg:w-60 border-r border-sidebar-border bg-sidebar text-sidebar-foreground flex flex-col items-center py-4 shrink-0 z-20 overflow-y-auto overscroll-y-contain">
        <div className="flex flex-col items-center w-full gap-6">
          {/* App Logo */}
          <div
            className="flex min-h-10 items-center gap-3 px-3 lg:w-full lg:px-5"
            title={es.app.title}
          >
            <span className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-sidebar-primary text-sidebar-primary-foreground">
              <FileCheck aria-hidden="true" className="size-5" />
            </span>
            <span className="hidden text-sm leading-5 font-semibold lg:block">{es.app.title}</span>
          </div>

          {/* Navigation Icons */}
          <nav className="flex flex-col items-center w-full gap-2 px-2 lg:px-3" aria-label={es.nav.label}>
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
                    "h-auto min-h-11 w-full flex-col gap-1 whitespace-normal px-1 py-3 text-xs leading-4 lg:flex-row lg:justify-start lg:gap-3 lg:px-3 lg:text-sm lg:leading-5 focus-visible:ring-0 focus-visible:outline-2 focus-visible:outline-sidebar-primary focus-visible:outline-offset-2",
                    isActive
                      ? "bg-sidebar-primary text-sidebar-primary-foreground font-semibold hover:bg-sidebar-primary hover:text-sidebar-primary-foreground"
                      : "text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
                  )}
                >
                  <Icon aria-hidden="true" className="size-5" />
                  <span className="text-center lg:text-left">{item.label}</span>
                </Button>
              );
            })}
          </nav>
        </div>

      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 h-full overflow-hidden">
        {/* Top Header */}
        <header className="h-12 bg-white border-b border-slate-200 px-4 flex items-center justify-between shrink-0 z-10">
          {/* Dynamic Breadcrumbs */}
          <nav aria-label="Migas de pan" className="flex min-w-0 items-center gap-2 text-slate-500 text-[13px]">
            {canGoBack && (
              <button
                type="button"
                onClick={breadcrumbs[0]?.onClick}
                className="p-1 hover:bg-slate-100 rounded text-slate-400 hover:text-slate-700"
                title={es.header.back}
                aria-label={es.header.back}
              >
                <ArrowLeft aria-hidden="true" className="w-4 h-4" />
              </button>
            )}

            {breadcrumbs.map((crumb, idx) => {
              const isLast = idx === breadcrumbs.length - 1;
              return (
                <div key={crumb.label} className="flex min-w-0 items-center gap-2">
                  {idx > 0 && <span className="text-slate-300">/</span>}
                  {isLast ? (
                    <span className="truncate font-semibold text-slate-800" aria-current="page">
                      {crumb.label}
                    </span>
                  ) : crumb.onClick ? (
                    <button
                      type="button"
                      onClick={crumb.onClick}
                      className="hover:underline text-slate-500 hover:text-slate-700 cursor-pointer"
                    >
                      {crumb.label}
                    </button>
                  ) : (
                    <span>{crumb.label}</span>
                  )}
                </div>
              );
            })}
          </nav>

        </header>

        {/* Content Slot */}
        <div className="flex-1 flex overflow-hidden min-h-0">{children}</div>
      </div>
    </div>
  );
}
