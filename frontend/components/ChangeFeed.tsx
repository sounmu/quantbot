"use client";

import Link from "next/link";
import { ChangeBadge, DeltaValue } from "@/components/TradeVisuals";
import type { HoldingChange } from "@/lib/types";

type Props = {
  changes: HoldingChange[];
  showEtf?: boolean;
  isLoading?: boolean;
};

export function ChangeFeed({ changes, showEtf = false, isLoading }: Props) {
  return (
    <div className="overflow-hidden rounded-lg border border-line bg-white shadow-soft">
      <table className="w-full min-w-[820px] border-collapse text-left text-sm">
        <thead className="bg-panel text-xs font-semibold uppercase tracking-normal text-muted">
          <tr>
            {showEtf ? <th className="px-4 py-3">ETF</th> : null}
            <th className="px-4 py-3">날짜</th>
            <th className="px-4 py-3">변동</th>
            <th className="px-4 py-3">종목</th>
            <th className="px-4 py-3">이름</th>
            <th className="px-4 py-3 text-right">주식수 Δ</th>
            <th className="px-4 py-3 text-right">비중 Δ</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-line">
          {isLoading ? (
            <tr>
              <td className="px-4 py-8 text-center text-muted" colSpan={showEtf ? 7 : 6}>
                불러오는 중
              </td>
            </tr>
          ) : changes.length === 0 ? (
            <tr>
              <td className="px-4 py-8 text-center text-muted" colSpan={showEtf ? 7 : 6}>
                변동 데이터 없음
              </td>
            </tr>
          ) : (
            changes.map((change) => (
              <tr key={`${change.ticker}-${change.as_of_date}-${change.holding_ticker}-${change.holding_name}`}>
                {showEtf ? (
                  <td className="px-4 py-3 font-semibold text-cobalt">
                    <Link href={`/etfs/${change.ticker}`}>{change.ticker}</Link>
                  </td>
                ) : null}
                <td className="px-4 py-3 text-muted">{change.as_of_date}</td>
                <td className="px-4 py-3">
                  <ChangeBadge type={change.change_type} />
                </td>
                <td className="px-4 py-3 font-semibold text-ink">{change.holding_ticker ?? "-"}</td>
                <td className="px-4 py-3 text-muted">{change.holding_name}</td>
                <td className="px-4 py-3 text-right">
                  <DeltaValue value={change.shares_delta} suffix="" />
                </td>
                <td className="px-4 py-3 text-right">
                  <DeltaValue value={change.weight_delta} suffix="%" />
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
