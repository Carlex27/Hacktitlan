import type { PropsWithChildren } from "react";

export function AppShell({ children }: PropsWithChildren) {
  return (
    <div className="app-shell">
      <header>
        <h1>Clasificador LIGIE</h1>
      </header>
      <main>{children}</main>
    </div>
  );
}
