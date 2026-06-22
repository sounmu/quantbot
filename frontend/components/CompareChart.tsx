"use client";

import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";
import type { CompareResponse } from "@/lib/types";

const COLORS = ["#2563eb", "#0f766e", "#be185d", "#7c3aed", "#ea580c", "#475569"];

export function CompareChart({
  data,
  isLoading,
  errorMessage
}: {
  data: CompareResponse | undefined;
  isLoading?: boolean;
  errorMessage?: string;
}) {
  const merged = mergeSeries(data);
  const tickers = data?.items.map((item) => item.ticker) ?? [];

  return (
    <div className="h-[360px] rounded-lg border border-line bg-white p-4 shadow-soft">
      {errorMessage ? (
        <div className="flex h-full items-center justify-center text-sm text-berry">
          {errorMessage}
        </div>
      ) : isLoading ? (
        <div className="flex h-full items-center justify-center text-sm text-muted">불러오는 중</div>
      ) : merged.length === 0 ? (
        <div className="flex h-full items-center justify-center text-sm text-muted">비교 데이터 없음</div>
      ) : (
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={merged} margin={{ top: 8, right: 18, left: 0, bottom: 8 }}>
            <CartesianGrid stroke="#d7dee8" strokeDasharray="3 3" />
            <XAxis dataKey="date" tick={{ fontSize: 12 }} minTickGap={28} />
            <YAxis tick={{ fontSize: 12 }} width={58} unit="%" />
            <Tooltip formatter={(value, name) => [`${Number(value).toFixed(2)}%`, name]} />
            {tickers.map((ticker, index) => (
              <Line
                key={ticker}
                type="monotone"
                dataKey={ticker}
                stroke={COLORS[index % COLORS.length]}
                strokeWidth={2}
                dot={false}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}

function mergeSeries(data: CompareResponse | undefined) {
  if (!data) {
    return [];
  }

  const rows = new Map<string, Record<string, string | number>>();
  Object.entries(data.series).forEach(([ticker, points]) => {
    points.forEach((point) => {
      const row = rows.get(point.date) ?? { date: point.date };
      row[ticker] = point.normalized_return;
      rows.set(point.date, row);
    });
  });

  return Array.from(rows.values()).sort((a, b) => String(a.date).localeCompare(String(b.date)));
}
