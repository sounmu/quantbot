"use client";

import Link from "next/link";
import { ChevronRight, Star } from "lucide-react";
import { CardSkeletonList } from "@/components/Skeleton";
import type { EtfListItem } from "@/lib/types";

type Props = {
  items: EtfListItem[];
  isLoading: boolean;
  errorMessage?: string;
  watchlist: {
    has: (ticker: string) => boolean;
    toggle: (ticker: string) => void;
  };
};

export function EtfTable({ items, isLoading, errorMessage, watchlist }: Props) {
  if (errorMessage) {
    return (
      <section aria-label="ETF 목록">
        <StatusCard tone="error">{errorMessage}</StatusCard>
      </section>
    );
  }
  if (isLoading) {
    return (
      <section aria-label="ETF 목록">
        <div className="lg:hidden">
          <CardSkeletonList count={6} metrics={3} />
        </div>
        <div className="hidden lg:block">
          <StatusCard>불러오는 중</StatusCard>
        </div>
      </section>
    );
  }
  if (items.length === 0) {
    return (
      <section aria-label="ETF 목록">
        <StatusCard>결과 없음</StatusCard>
      </section>
    );
  }

  return (
    <section aria-label="ETF 목록">
      {/* 모바일: 카드 리스트 */}
      <div className="space-y-3 lg:hidden" role="list">
        {items.map((item) => (
          <EtfCard key={item.ticker} item={item} watchlist={watchlist} />
        ))}
      </div>

      {/* 데스크탑: 테이블 */}
      <div className="hidden overflow-hidden rounded-lg border border-line bg-surface lg:block">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-line text-left text-xs font-semibold text-faint">
              <Th className="pl-4">티커</Th>
              <Th>이름</Th>
              <Th>운용사</Th>
              <Th>테마</Th>
              <Th className="text-right">보수율</Th>
              <Th className="text-right">YTD</Th>
              <Th className="text-right">1Y</Th>
              <Th className="pr-4 text-center">관심</Th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => {
              const isWatching = watchlist.has(item.ticker);
              return (
                <tr
                  key={item.ticker}
                  className="group border-b border-hair last:border-0 transition hover:bg-panel"
                >
                  <td className="py-3 pl-4">
                    <Link
                      href={`/etfs/${item.ticker}`}
                      className="inline-flex items-center gap-1 font-bold tracking-tight text-ink"
                      aria-label={`${item.ticker} 상세 보기`}
                    >
                      {item.ticker}
                      <ChevronRight className="h-3.5 w-3.5 text-faint opacity-0 transition group-hover:opacity-100" aria-hidden="true" />
                    </Link>
                  </td>
                  <td className="max-w-[280px] py-3 pr-3">
                    <Link href={`/etfs/${item.ticker}`} className="block truncate text-body hover:text-brand">
                      {item.name}
                    </Link>
                  </td>
                  <td className="py-3 pr-3 text-muted">{item.issuer}</td>
                  <td className="py-3 pr-3 text-muted">{item.theme ?? "-"}</td>
                  <td className="py-3 pr-3 text-right tabular-nums text-ink">{formatPercent(item.expense_ratio)}</td>
                  <td className="py-3 pr-3 text-right tabular-nums">{formatReturn(item.return_ytd)}</td>
                  <td className="py-3 pr-3 text-right tabular-nums">{formatReturn(item.return_1y)}</td>
                  <td className="py-3 pr-4 text-center">
                    <button
                      className="inline-flex h-9 w-9 items-center justify-center rounded-md text-muted transition hover:bg-surface hover:text-berry"
                      onClick={() => watchlist.toggle(item.ticker)}
                      title="관심목록"
                      aria-label={isWatching ? `${item.ticker} 관심목록에서 제거` : `${item.ticker} 관심목록에 추가`}
                      aria-pressed={isWatching}
                    >
                      <Star className="h-[18px] w-[18px]" fill={isWatching ? "currentColor" : "none"} aria-hidden="true" />
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function EtfCard({ item, watchlist }: { item: EtfListItem; watchlist: Props["watchlist"] }) {
  const isWatching = watchlist.has(item.ticker);
  return (
    <article
      className="rounded-lg border border-line bg-surface p-4 transition hover:border-line-strong"
      role="listitem"
    >
      <div className="flex items-start gap-3">
        <Link
          className="min-w-0 flex-1 rounded-md focus:outline-none focus-visible:ring-2 focus-visible:ring-cobalt"
          href={`/etfs/${item.ticker}`}
          aria-label={`${item.ticker} 상세 보기`}
        >
          <div className="flex items-center gap-1.5">
            <span className="text-lg font-bold leading-none tracking-tight text-ink">{item.ticker}</span>
            <ChevronRight className="h-4 w-4 text-faint" aria-hidden="true" />
          </div>
          <h2 className="mt-2 text-sm font-medium leading-snug text-body">{item.name}</h2>
          <p className="mt-1 text-xs text-muted">
            {item.issuer}
            {item.theme ? ` · ${item.theme}` : ""}
          </p>
        </Link>

        <button
          className="inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-md text-muted hover:bg-panel hover:text-berry"
          onClick={() => watchlist.toggle(item.ticker)}
          title="관심목록"
          aria-label={isWatching ? `${item.ticker} 관심목록에서 제거` : `${item.ticker} 관심목록에 추가`}
          aria-pressed={isWatching}
        >
          <Star className="h-5 w-5" fill={isWatching ? "currentColor" : "none"} aria-hidden="true" />
        </button>
      </div>

      <div className="mt-4 grid grid-cols-3 gap-2 border-t border-hair pt-3 text-xs">
        <Metric label="보수율" value={formatPercent(item.expense_ratio)} />
        <Metric label="YTD" value={formatReturn(item.return_ytd)} />
        <Metric label="1Y" value={formatReturn(item.return_1y)} />
      </div>
    </article>
  );
}

function Th({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <th className={`px-3 py-2.5 font-semibold ${className}`}>{children}</th>;
}

function StatusCard({ children, tone = "muted" }: { children: React.ReactNode; tone?: "muted" | "error" }) {
  return (
    <div
      className={`rounded-lg border border-line bg-surface px-4 py-10 text-center text-sm ${
        tone === "error" ? "text-rise" : "text-muted"
      }`}
    >
      {children}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="min-w-0">
      <div className="text-[11px] text-faint">{label}</div>
      <div className="mt-1 truncate text-sm font-semibold tabular-nums text-ink">{value}</div>
    </div>
  );
}

function formatPercent(value: number | null) {
  return value === null ? "-" : `${value.toFixed(2)}%`;
}

function formatReturn(value: number | null) {
  if (value === null) {
    return "-";
  }
  const color = value >= 0 ? "text-rise" : "text-fall";
  return <span className={color}>{value.toFixed(2)}%</span>;
}
