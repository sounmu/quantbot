"use client";

import Link from "next/link";
import { Star } from "lucide-react";
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
    <div className="overflow-hidden rounded-lg border border-line bg-white shadow-soft">
      <div className="overflow-x-auto">
        <table className="w-full min-w-[880px] border-collapse text-left text-sm">
          <thead className="bg-panel text-xs font-semibold uppercase tracking-normal text-muted">
            <tr>
              <th className="w-12 px-4 py-3"></th>
              <th className="px-4 py-3">티커</th>
              <th className="px-4 py-3">이름</th>
              <th className="px-4 py-3">운용사</th>
              <th className="px-4 py-3">테마</th>
              <th className="px-4 py-3 text-right">보수율</th>
              <th className="px-4 py-3 text-right">YTD</th>
              <th className="px-4 py-3 text-right">1Y</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {errorMessage ? (
              <tr>
                <td className="px-4 py-8 text-center text-berry" colSpan={8}>
                  {errorMessage}
                </td>
              </tr>
            ) : isLoading ? (
              <tr>
                <td className="px-4 py-8 text-center text-muted" colSpan={8}>
                  불러오는 중
                </td>
              </tr>
            ) : items.length === 0 ? (
              <tr>
                <td className="px-4 py-8 text-center text-muted" colSpan={8}>
                  결과 없음
                </td>
              </tr>
            ) : (
              items.map((item) => (
                <tr key={item.ticker} className="hover:bg-panel/70">
                  <td className="px-4 py-3">
                    <button
                      className="inline-flex h-8 w-8 items-center justify-center rounded-md text-muted hover:bg-white hover:text-berry"
                      onClick={() => watchlist.toggle(item.ticker)}
                      title="관심목록"
                      aria-label={
                        watchlist.has(item.ticker) ? "관심목록에서 제거" : "관심목록에 추가"
                      }
                      aria-pressed={watchlist.has(item.ticker)}
                    >
                      <Star
                        className="h-4 w-4"
                        fill={watchlist.has(item.ticker) ? "currentColor" : "none"}
                        aria-hidden="true"
                      />
                    </button>
                  </td>
                  <td className="px-4 py-3 font-semibold text-cobalt">
                    <Link href={`/etfs/${item.ticker}`}>{item.ticker}</Link>
                  </td>
                  <td className="max-w-[320px] px-4 py-3 text-ink">
                    <Link href={`/etfs/${item.ticker}`}>{item.name}</Link>
                  </td>
                  <td className="px-4 py-3 text-muted">{item.issuer}</td>
                  <td className="px-4 py-3 text-muted">{item.theme ?? "-"}</td>
                  <td className="px-4 py-3 text-right">{formatPercent(item.expense_ratio)}</td>
                  <td className="px-4 py-3 text-right">{formatReturn(item.return_ytd)}</td>
                  <td className="px-4 py-3 text-right">{formatReturn(item.return_1y)}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
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
  const color = value >= 0 ? "text-accent" : "text-berry";
  return <span className={color}>{value.toFixed(2)}%</span>;
}
