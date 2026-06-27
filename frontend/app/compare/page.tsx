"use client";

import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { CompareChart } from "@/components/CompareChart";
import { useCompare } from "@/hooks/useCompare";
import { useWatchlist } from "@/hooks/useWatchlist";
import { useState } from "react";

const RANGES = ["1m", "3m", "6m", "1y", "ytd", "max"];

export default function ComparePage() {
  const watchlist = useWatchlist();
  const [range, setRange] = useState("1y");
  const compare = useCompare(watchlist.tickers, range);

  return (
    <AppShell>
      <div className="mb-5 space-y-3">
        <Link className="inline-flex min-h-11 items-center gap-2 text-sm text-muted hover:text-ink" href="/etfs">
          <ArrowLeft className="h-4 w-4" aria-hidden="true" />
          목록
        </Link>
        <div className="grid grid-cols-6 rounded-lg bg-panel p-1 sm:inline-grid sm:w-auto sm:grid-flow-col">
          {RANGES.map((item) => (
            <button
              key={item}
              className={`h-10 rounded-md px-1 text-xs font-semibold transition sm:px-4 ${
                range === item ? "bg-surface text-ink shadow-soft" : "text-muted hover:text-body"
              }`}
              onClick={() => setRange(item)}
            >
              {item.toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      <div className="mb-5">
        <h1 className="text-2xl font-bold leading-tight tracking-tight text-ink">관심 ETF 비교</h1>
        <p className="mt-2 text-sm leading-snug text-muted">
          {!watchlist.isReady
            ? "관심목록을 불러오는 중입니다."
            : watchlist.tickers.length >= 2
              ? watchlist.tickers.join(", ")
              : "목록에서 2개 이상을 관심목록에 추가하세요."}
        </p>
      </div>

      <CompareChart
        data={compare.data}
        isLoading={watchlist.isReady && compare.isLoading}
        errorMessage={compare.isError ? "비교 데이터를 불러오지 못했습니다." : undefined}
      />

      <section className="mt-6" aria-label="비교 ETF">
        {!watchlist.isReady || compare.isLoading ? (
          <StatusCard>불러오는 중</StatusCard>
        ) : compare.isError ? (
          <StatusCard tone="error">비교 데이터를 불러오지 못했습니다.</StatusCard>
        ) : (compare.data?.items ?? []).length === 0 ? (
          <StatusCard>비교할 ETF가 없습니다.</StatusCard>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {(compare.data?.items ?? []).map((item) => (
              <article key={item.ticker} className="rounded-lg border border-line bg-surface p-4 transition hover:border-line-strong">
                <Link className="text-lg font-bold leading-none tracking-tight text-ink" href={`/etfs/${item.ticker}`}>
                  {item.ticker}
                </Link>
                <h2 className="mt-2 text-sm font-medium leading-snug text-body">{item.name}</h2>
                <p className="mt-1 text-xs text-muted">{item.issuer}</p>
                <div className="mt-4 grid grid-cols-3 gap-2 border-t border-hair pt-3 text-xs">
                  <Metric label="보수율" value={formatPercent(item.expense_ratio)} />
                  <Metric label="YTD" value={formatReturn(item.return_ytd)} />
                  <Metric label="1Y" value={formatReturn(item.return_1y)} />
                </div>
              </article>
            ))}
          </div>
        )}
      </section>
    </AppShell>
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
  return <span className={value >= 0 ? "text-rise" : "text-fall"}>{value.toFixed(2)}%</span>;
}
