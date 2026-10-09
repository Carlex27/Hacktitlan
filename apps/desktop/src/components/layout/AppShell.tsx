import type { ComponentType, ReactNode } from "react";
import { ArrowLeft, Bell, FileCheck, Search } from "lucide-react";

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
    <div className="flex h-screen w-screen overflow-hidden bg-app-canvas font-sans text-slate-800 text-[13px] antialiased">
      {/* Left Sidebar */}
      <aside className="w-[72px] bg-sidebar-bg text-slate-400 flex flex-col items-center py-3 justify-between shrink-0 z-20">
        <div className="flex flex-col items-center w-full gap-4">
          {/* App Logo */}
          <div
            className="w-10 h-10 rounded-xl bg-blue-600 flex items-center justify-center text-white shadow-md shadow-blue-500/30"
            title={es.app.title}
          >
            <FileCheck aria-hidden="true" className="w-5 h-5" />
          </div>

          {/* Navigation Icons */}
          <nav className="flex flex-col items-center w-full gap-1.5 pt-1" aria-label="Navegación principal">
            {items.map((item) => {
              const Icon = item.icon;
              const isActive = item.id === activeId;

              if (item.disabled) {
                return (
                  <button
                    key={item.id}
                    type="button"
                    disabled
                    aria-disabled="true"
                    title={`${item.label} (${es.nav.comingSoon})`}
                    className="w-full flex flex-col items-center py-2.5 text-slate-600 cursor-not-allowed opacity-50 select-none"
                  >
                    <Icon aria-hidden="true" className="w-5 h-5 mb-1" />
                    <span className="text-[10px] font-medium tracking-tight">{item.label}</span>
                  </button>
                );
              }

              return (
                <button
                  key={item.id}
                  type="button"
                  aria-current={isActive ? "page" : undefined}
                  onClick={() => onNavigate(item.id)}
                  title={item.label}
                  className={cn(
                    "w-full flex flex-col items-center py-2.5 transition-colors select-none",
                    isActive
                      ? "text-blue-400 border-l-[3px] border-blue-500 bg-sidebar-hover font-semibold"
                      : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/60",
                  )}
                >
                  <Icon aria-hidden="true" className="w-5 h-5 mb-1" />
                  <span className="text-[10px] font-medium tracking-tight">{item.label}</span>
                </button>
              );
            })}
          </nav>
        </div>

        {/* Note: User profile removed per PRODUCT_DECISIONS (no user accounts) */}
        <div className="w-full h-8" aria-hidden="true" />
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

          {/* Search & Header Actions (disabled to avoid deceiving users) */}
          <div className="flex items-center gap-3">
            {/* Search Bar (Disabled) */}
            <div className="relative w-72" title={es.header.searchTooltip}>
              <Search aria-hidden="true" className="w-4 h-4 absolute left-3 top-2.5 text-slate-400" />
              <input
                disabled
                className="w-full bg-slate-100/70 text-xs pl-9 pr-3 py-1.5 rounded-md border border-slate-200 cursor-not-allowed text-slate-400 placeholder:text-slate-400 select-none"
                placeholder={es.header.searchPlaceholder}
                type="text"
              />
            </div>

            {/* Notification Bell (Disabled) */}
            <button
              type="button"
              disabled
              aria-disabled="true"
              className="p-1.5 text-slate-400 cursor-not-allowed rounded-full select-none"
              title={es.header.notificationsTooltip}
            >
              <Bell aria-hidden="true" className="w-5 h-5" />
            </button>
          </div>
        </header>

        {/* Content Slot */}
        <div className="flex-1 flex overflow-hidden min-h-0">{children}</div>
      </div>
    </div>
  );
}
