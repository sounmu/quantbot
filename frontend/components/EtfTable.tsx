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
  return (
    <section className="space-y-3" aria-label="ETF 목록">
      {errorMessage ? (
        <StatusCard tone="error">{errorMessage}</StatusCard>
      ) : isLoading ? (
        <CardSkeletonList count={6} metrics={3} />
      ) : items.length === 0 ? (
        <StatusCard>결과 없음</StatusCard>
      ) : (
        <div className="space-y-3" role="list">
          {items.map((item) => {
            const isWatching = watchlist.has(item.ticker);
            return (
              <article
                key={item.ticker}
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
                    <Star
                      className="h-5 w-5"
                      fill={isWatching ? "currentColor" : "none"}
                      aria-hidden="true"
                    />
                  </button>
                </div>

                <div className="mt-4 grid grid-cols-3 gap-2 border-t border-hair pt-3 text-xs">
                  <Metric label="보수율" value={formatPercent(item.expense_ratio)} />
                  <Metric label="YTD" value={formatReturn(item.return_ytd)} />
                  <Metric label="1Y" value={formatReturn(item.return_1y)} />
                </div>
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
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
