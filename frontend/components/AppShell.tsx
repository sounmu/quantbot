import Link from "next/link";
import { Activity, BarChart3, GitCompare, Table2 } from "lucide-react";

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <main className="min-h-screen">
      <header className="border-b border-line bg-white">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-5">
          <Link href="/etfs" className="flex items-center gap-2 font-semibold text-ink">
            <BarChart3 className="h-5 w-5 text-accent" aria-hidden="true" />
            Quantbot
          </Link>
          <nav className="flex items-center gap-1 text-sm">
            <Link
              className="inline-flex h-9 items-center gap-2 rounded-md px-3 text-muted hover:bg-panel hover:text-ink"
              href="/etfs"
            >
              <Table2 className="h-4 w-4" aria-hidden="true" />
              ETF
            </Link>
            <Link
              className="inline-flex h-9 items-center gap-2 rounded-md px-3 text-muted hover:bg-panel hover:text-ink"
              href="/compare"
            >
              <GitCompare className="h-4 w-4" aria-hidden="true" />
              비교
            </Link>
            <Link
              className="inline-flex h-9 items-center gap-2 rounded-md px-3 text-muted hover:bg-panel hover:text-ink"
              href="/changes"
            >
              <Activity className="h-4 w-4" aria-hidden="true" />
              매매
            </Link>
          </nav>
        </div>
      </header>
      <div className="mx-auto max-w-7xl px-5 py-6">{children}</div>
    </main>
  );
}
