"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Activity, BarChart3, GitCompare, LineChart, Moon, Sun, Table2 } from "lucide-react";
import { useTheme } from "@/components/ThemeProvider";

const TABS = [
  { href: "/etfs", label: "목록", icon: Table2 },
  { href: "/changes", label: "피드", icon: Activity },
  { href: "/analysis", label: "분석", icon: LineChart },
  { href: "/compare", label: "비교", icon: GitCompare }
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="min-h-screen bg-canvas">
      <main className="mx-auto min-h-screen w-full max-w-[480px] overflow-x-hidden bg-panel shadow-frame">
        <header className="sticky top-0 z-20 border-b border-line bg-surface/80 backdrop-blur">
          <div className="flex h-14 items-center justify-between px-4">
            <Link href="/etfs" className="flex min-h-11 items-center gap-2 text-[15px] font-semibold tracking-tight text-ink">
              <BarChart3 className="h-5 w-5 text-brand" aria-hidden="true" />
              Quantbot
            </Link>
            <div className="flex items-center gap-2">
              <span className="rounded-full bg-brand-soft px-2.5 py-1 text-[11px] font-semibold text-brand">
                shares Δ
              </span>
              <ThemeToggle />
            </div>
          </div>
        </header>

        <div className="px-4 pb-[calc(96px+env(safe-area-inset-bottom))] pt-5">{children}</div>
      </main>

      <nav
        className="fixed bottom-0 left-1/2 z-30 w-full max-w-[480px] -translate-x-1/2 border-t border-line bg-surface/80 px-3 pb-[calc(10px+env(safe-area-inset-bottom))] pt-2 backdrop-blur"
        aria-label="주요 화면"
      >
        <div className="grid grid-cols-4 gap-1">
          {TABS.map((tab) => {
            const Icon = tab.icon;
            const isActive = pathname === tab.href || pathname.startsWith(`${tab.href}/`);
            return (
              <Link
                key={tab.href}
                href={tab.href}
                aria-label={tab.label}
                aria-current={isActive ? "page" : undefined}
                className={`flex min-h-12 flex-col items-center justify-center gap-1 rounded-lg px-1 text-[11px] font-medium transition ${
                  isActive ? "bg-brand-soft text-brand" : "text-faint hover:bg-panel hover:text-body"
                }`}
              >
                <Icon className="h-5 w-5" strokeWidth={isActive ? 2.4 : 2} aria-hidden="true" />
                <span>{tab.label}</span>
              </Link>
            );
          })}
        </div>
      </nav>
    </div>
  );
}

function ThemeToggle() {
  const { theme, toggle } = useTheme();
  const isDark = theme === "dark";

  return (
    <button
      type="button"
      onClick={toggle}
      className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-line text-muted transition hover:border-line-strong hover:text-ink"
      aria-label={isDark ? "라이트 모드로 전환" : "다크 모드로 전환"}
      title={isDark ? "라이트 모드" : "다크 모드"}
    >
      {isDark ? (
        <Sun className="h-[18px] w-[18px]" aria-hidden="true" />
      ) : (
        <Moon className="h-[18px] w-[18px]" aria-hidden="true" />
      )}
    </button>
  );
}
