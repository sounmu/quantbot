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
      <div className="mb-5 flex items-center justify-between">
        <Link className="inline-flex items-center gap-2 text-sm text-muted hover:text-ink" href="/etfs">
          <ArrowLeft className="h-4 w-4" aria-hidden="true" />
          목록
        </Link>
        <div className="flex rounded-md border border-line bg-white p-1">
          {RANGES.map((item) => (
            <button
              key={item}
              className={`h-8 min-w-12 rounded px-3 text-xs font-medium ${
                range === item ? "bg-ink text-white" : "text-muted hover:bg-panel"
              }`}
              onClick={() => setRange(item)}
            >
              {item.toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      <div className="mb-5">
        <h1 className="text-2xl font-semibold text-ink">관심 ETF 비교</h1>
        <p className="mt-1 text-sm text-muted">
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

      <div className="mt-6 overflow-hidden rounded-lg border border-line bg-white shadow-soft">
        <table className="w-full min-w-[760px] border-collapse text-left text-sm">
          <thead className="bg-panel text-xs font-semibold uppercase tracking-normal text-muted">
            <tr>
              <th className="px-4 py-3">티커</th>
              <th className="px-4 py-3">이름</th>
              <th className="px-4 py-3">운용사</th>
              <th className="px-4 py-3 text-right">보수율</th>
              <th className="px-4 py-3 text-right">YTD</th>
              <th className="px-4 py-3 text-right">1Y</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {!watchlist.isReady || compare.isLoading ? (
              <tr>
                <td className="px-4 py-8 text-center text-muted" colSpan={6}>
                  불러오는 중
                </td>
              </tr>
            ) : compare.isError ? (
              <tr>
                <td className="px-4 py-8 text-center text-berry" colSpan={6}>
                  비교 데이터를 불러오지 못했습니다.
                </td>
              </tr>
            ) : (compare.data?.items ?? []).length === 0 ? (
              <tr>
                <td className="px-4 py-8 text-center text-muted" colSpan={6}>
                  비교할 ETF가 없습니다.
                </td>
              </tr>
            ) : (
              (compare.data?.items ?? []).map((item) => (
                <tr key={item.ticker}>
                  <td className="px-4 py-3 font-semibold text-cobalt">
                    <Link href={`/etfs/${item.ticker}`}>{item.ticker}</Link>
                  </td>
                  <td className="px-4 py-3 text-ink">{item.name}</td>
                  <td className="px-4 py-3 text-muted">{item.issuer}</td>
                  <td className="px-4 py-3 text-right">{formatPercent(item.expense_ratio)}</td>
                  <td className="px-4 py-3 text-right">{formatReturn(item.return_ytd)}</td>
                  <td className="px-4 py-3 text-right">{formatReturn(item.return_1y)}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </AppShell>
  );
}

function formatPercent(value: number | null) {
  return value === null ? "-" : `${value.toFixed(2)}%`;
}

function formatReturn(value: number | null) {
  if (value === null) {
    return "-";
  }
  return <span className={value >= 0 ? "text-accent" : "text-berry"}>{value.toFixed(2)}%</span>;
}
