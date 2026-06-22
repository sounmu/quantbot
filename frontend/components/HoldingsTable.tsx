"use client";

import { ChangeBadge, DeltaValue } from "@/components/TradeVisuals";
import type { Holding } from "@/lib/types";

type Props = {
  holdings: Holding[];
  selectedKey?: string | null;
  onSelect?: (holdingKey: string, label: string) => void;
};

export function HoldingsTable({ holdings, selectedKey, onSelect }: Props) {
  return (
    <div className="overflow-hidden rounded-lg border border-line bg-white shadow-soft">
      <div className="overflow-x-auto">
        <table className="w-full min-w-[640px] table-fixed border-collapse text-left text-sm">
          <colgroup>
            <col className="w-[68px]" />
            <col className="w-[88px]" />
            <col />
            <col className="w-[104px]" />
            <col className="w-[104px]" />
            <col className="w-[80px]" />
            <col className="w-[96px]" />
          </colgroup>
          <thead className="bg-panel text-xs font-semibold uppercase tracking-normal text-muted">
            <tr>
              <th className="px-3 py-3">변동</th>
              <th className="px-3 py-3">종목</th>
              <th className="px-3 py-3">이름</th>
              <th className="px-3 py-3 text-right">주식수</th>
              <th className="px-3 py-3 text-right">주식수 Δ</th>
              <th className="px-3 py-3 text-right">비중</th>
              <th className="px-3 py-3 text-right">비중 Δ</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {holdings.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-muted">
                  보유종목 데이터 없음
                </td>
              </tr>
            ) : (
              holdings.map((holding) => {
                const key = positionKey(holding);
                return (
                  <tr
                    key={`${holding.as_of_date}-${holding.holding_ticker}-${holding.holding_name}`}
                    className={`cursor-pointer hover:bg-panel/70 ${selectedKey === key ? "bg-panel" : ""}`}
                    onClick={() => onSelect?.(key, holding.holding_ticker ?? holding.holding_name)}
                  >
                    <td className="px-3 py-3 align-middle">
                      <ChangeBadge type={holding.change_type} compact />
                    </td>
                    <td className="px-3 py-3 font-semibold text-ink">
                      {holding.holding_ticker ?? "-"}
                    </td>
                    <td className="truncate px-3 py-3 text-muted" title={holding.holding_name}>
                      {holding.holding_name}
                    </td>
                    <td className="px-3 py-3 text-right">{formatNumber(holding.shares)}</td>
                    <td className="px-3 py-3 text-right">
                      <DeltaValue value={holding.shares_delta} suffix="" />
                    </td>
                    <td className="px-3 py-3 text-right">{holding.weight.toFixed(2)}%</td>
                    <td className="px-3 py-3 text-right">
                      <DeltaValue value={holding.weight_delta} suffix="%" />
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function formatNumber(value: number | null) {
  return value === null ? "-" : Math.round(value).toLocaleString();
}

function positionKey(holding: Holding) {
  if (holding.holding_ticker) {
    return holding.holding_ticker;
  }
  return `NAME:${holding.holding_name.toUpperCase().replace(/[^A-Z0-9]/g, "")}`;
}
