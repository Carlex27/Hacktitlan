import type { PropsWithChildren } from "react";
import {
  ArrowLeft,
  BarChart3,
  Bell,
  CheckCircle,
  ChevronRight,
  Clock,
  FileCheck,
  FileText,
  Search,
  Settings,
} from "lucide-react";

export function AppShell({ children }: PropsWithChildren) {
  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[#EEF2F6] font-sans text-slate-800 text-[13px] antialiased select-none">
      {/* Left Sidebar */}
      <aside className="w-[72px] bg-[#121824] text-slate-400 flex flex-col items-center py-3 justify-between shrink-0 z-20">
        <div className="flex flex-col items-center w-full space-y-4">
          {/* App Logo */}
          <div
            className="w-10 h-10 rounded-xl bg-blue-600 flex items-center justify-center text-white shadow-md shadow-blue-500/30 cursor-pointer"
            title="Clasificador LIGIE"
          >
            <FileCheck className="w-5 h-5" />
          </div>

          {/* Navigation Icons */}
          <nav className="flex flex-col items-center w-full space-y-1.5 pt-1">
            {/* Documents (Active) */}
            <button
              type="button"
              className="w-full flex flex-col items-center py-2.5 text-blue-400 border-l-[3px] border-blue-500 bg-[#1e2638] transition-colors"
              title="Documentos"
            >
              <FileText className="w-5 h-5 mb-1" />
              <span className="text-[10px] font-medium tracking-tight">Documentos</span>
            </button>

            {/* Validation */}
            <button
              type="button"
              className="w-full flex flex-col items-center py-2.5 text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 transition-colors"
              title="Validación"
            >
              <CheckCircle className="w-5 h-5 mb-1" />
              <span className="text-[10px] font-medium tracking-tight">Validación</span>
            </button>

            {/* History */}
            <button
              type="button"
              className="w-full flex flex-col items-center py-2.5 text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 transition-colors"
              title="Historial"
            >
              <Clock className="w-5 h-5 mb-1" />
              <span className="text-[10px] font-medium tracking-tight">Historial</span>
            </button>

            {/* Reports */}
            <button
              type="button"
              className="w-full flex flex-col items-center py-2.5 text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 transition-colors"
              title="Reportes"
            >
              <BarChart3 className="w-5 h-5 mb-1" />
              <span className="text-[10px] font-medium tracking-tight">Reportes</span>
            </button>

            {/* Settings */}
            <button
              type="button"
              className="w-full flex flex-col items-center py-2.5 text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 transition-colors"
              title="Configuración"
            >
              <Settings className="w-5 h-5 mb-1" />
              <span className="text-[10px] font-medium tracking-tight">Ajustes</span>
            </button>
          </nav>
        </div>

        {/* Bottom User Profile Pill */}
        <div className="flex items-center space-x-1 cursor-pointer group px-2 py-1.5 rounded-lg hover:bg-slate-800/80">
          <div className="w-8 h-8 rounded-full bg-slate-700 text-slate-200 text-xs font-semibold flex items-center justify-center border border-slate-600">
            JD
          </div>
          <ChevronRight className="w-3.5 h-3.5 text-slate-400 group-hover:text-white" />
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 h-full overflow-hidden">
        {/* Top Header */}
        <header className="h-12 bg-white border-b border-slate-200 px-4 flex items-center justify-between shrink-0 z-10">
          {/* Breadcrumbs */}
          <div className="flex items-center space-x-2 text-slate-500 text-[13px]">
            <button
              type="button"
              className="p-1 hover:bg-slate-100 rounded text-slate-400 hover:text-slate-700"
              title="Atrás"
            >
              <ArrowLeft className="w-4 h-4" />
            </button>
            <span className="hover:underline cursor-pointer">Aduanas</span>
            <span className="text-slate-300">/</span>
            <span className="hover:underline cursor-pointer">Validación Documental</span>
            <span className="text-slate-300">/</span>
            <span className="font-semibold text-slate-800">Acta de Molino</span>
          </div>

          {/* Search & Profile Actions */}
          <div className="flex items-center space-x-3">
            {/* Search Bar */}
            <div className="relative w-72">
              <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-400" />
              <input
                className="w-full bg-slate-50 hover:bg-slate-100/70 focus:bg-white text-xs pl-9 pr-3 py-1.5 rounded-md border border-slate-200 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 transition-all text-slate-700 placeholder:text-slate-400"
                placeholder="Buscar documentos, fracciones, proveedores..."
                type="text"
              />
            </div>

            {/* Notification Bell */}
            <button
              type="button"
              className="relative p-1.5 text-slate-500 hover:text-slate-700 hover:bg-slate-100 rounded-full"
              title="Notificaciones"
            >
              <Bell className="w-5 h-5" />
              <span className="absolute top-1.5 right-1.5 w-1.5 h-1.5 bg-red-500 rounded-full" />
            </button>

            {/* User Avatar with status dot */}
            <div className="relative cursor-pointer">
              <div className="w-7 h-7 rounded-full bg-slate-200 text-slate-600 flex items-center justify-center font-medium text-xs border border-slate-300">
                JD
              </div>
              <span className="absolute bottom-0 right-0 w-2 h-2 bg-emerald-500 rounded-full ring-2 ring-white" />
            </div>
          </div>
        </header>

        {/* Content Container */}
        <div className="flex-1 flex overflow-hidden min-h-0">{children}</div>
      </div>
    </div>
  );
}
