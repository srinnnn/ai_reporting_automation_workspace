import type { ReactNode } from "react";

type PlatformShellProps = {
  children: ReactNode;
  sidebar: ReactNode;
  topbar: ReactNode;
};

export function PlatformShell({ children, sidebar, topbar }: PlatformShellProps) {
  return (
    <div className="shell">
      {sidebar}
      <main className="main">
        {topbar}
        {children}
      </main>
    </div>
  );
}
