"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Activity, BarChart3, GitCompare, LineChart, Moon, Sun, Table2 } from "lucide-react";
import { useTheme } from "@/components/ThemeProvider";

const TABS = [
  { href: "/etfs", label: "목록", icon: Table2 },
  { href: "/changes", label: "매매", icon: Activity },
  { href: "/analysis", label: "분석", icon: LineChart },
  { href: "/compare", label: "비교", icon: GitCompare }
];

function isActive(pathname: string, href: string) {
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="min-h-screen bg-canvas">
      {/* 데스크탑: 좌측 고정 사이드바 */}
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-60 flex-col border-r border-line bg-surface lg:flex">
        <div className="flex h-16 items-center border-b border-line px-5">
          <Link
            href="/etfs"
            className="flex items-center gap-2 text-base font-semibold tracking-tight text-ink"
          >
            <BarChart3 className="h-5 w-5 text-brand" aria-hidden="true" />
            Quantbot
          </Link>
        </div>
        <nav className="flex-1 space-y-1 px-3 py-4" aria-label="주요 화면">
          {TABS.map((tab) => {
            const Icon = tab.icon;
            const active = isActive(pathname, tab.href);
            return (
              <Link
                key={tab.href}
                href={tab.href}
                aria-current={active ? "page" : undefined}
                className={`flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition ${
                  active ? "bg-brand-soft text-brand" : "text-muted hover:bg-panel hover:text-ink"
                }`}
              >
                <Icon className="h-5 w-5" strokeWidth={active ? 2.4 : 2} aria-hidden="true" />
                {tab.label}
              </Link>
            );
          })}
        </nav>
        <div className="flex items-center justify-between border-t border-line px-5 py-4">
          <span className="rounded-full bg-brand-soft px-2.5 py-1 text-[11px] font-semibold text-brand">
            주식수 기준
          </span>
          <ThemeToggle />
        </div>
      </aside>

      {/* 모바일: 상단 헤더 */}
      <header className="sticky top-0 z-20 border-b border-line bg-surface/80 backdrop-blur lg:hidden">
        <div className="flex h-14 items-center justify-between px-4">
          <Link
            href="/etfs"
            className="flex min-h-11 items-center gap-2 text-[15px] font-semibold tracking-tight text-ink"
          >
            <BarChart3 className="h-5 w-5 text-brand" aria-hidden="true" />
            Quantbot
          </Link>
          <div className="flex items-center gap-2">
            <span className="rounded-full bg-brand-soft px-2.5 py-1 text-[11px] font-semibold text-brand">
              주식수 기준
            </span>
            <ThemeToggle />
          </div>
        </div>
      </header>

      {/* 메인 콘텐츠: 데스크탑은 사이드바 폭만큼 왼쪽 패딩, 와이드 컨테이너 */}
      <main className="lg:pl-60">
        <div className="mx-auto w-full max-w-screen-2xl px-4 pb-[calc(96px+env(safe-area-inset-bottom))] pt-5 lg:px-8 lg:pb-12 lg:pt-8">
          {children}
        </div>
      </main>

      {/* 모바일: 하단 탭바 */}
      <nav
        className="fixed bottom-0 left-0 z-30 w-full border-t border-line bg-surface/80 px-3 pb-[calc(10px+env(safe-area-inset-bottom))] pt-2 backdrop-blur lg:hidden"
        aria-label="주요 화면"
      >
        <div className="grid grid-cols-4 gap-1">
          {TABS.map((tab) => {
            const Icon = tab.icon;
            const active = isActive(pathname, tab.href);
            return (
              <Link
                key={tab.href}
                href={tab.href}
                aria-label={tab.label}
                aria-current={active ? "page" : undefined}
                className={`flex min-h-12 flex-col items-center justify-center gap-1 rounded-lg px-1 text-[11px] font-medium transition ${
                  active ? "bg-brand-soft text-brand" : "text-faint hover:bg-panel hover:text-body"
                }`}
              >
                <Icon className="h-5 w-5" strokeWidth={active ? 2.4 : 2} aria-hidden="true" />
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
