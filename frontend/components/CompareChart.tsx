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
import { makeEndDot } from "@/components/chartHelpers";
import { ChartSkeleton } from "@/components/Skeleton";
import { useChartPalette } from "@/components/ThemeProvider";
import type { CompareResponse } from "@/lib/types";

const COLORS = ["#6366f1", "#14b8a6", "#ec4899", "#a855f7", "#f59e0b", "#94a3b8"];

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
  const palette = useChartPalette();

  return (
    <div className="h-[280px] rounded-lg border border-line bg-surface p-4">
      {errorMessage ? (
        <div className="flex h-full items-center justify-center text-sm text-rise">
          {errorMessage}
        </div>
      ) : isLoading ? (
        <ChartSkeleton height={248} />
      ) : merged.length === 0 ? (
        <div className="flex h-full items-center justify-center text-sm text-muted">비교 데이터 없음</div>
      ) : (
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={merged} margin={{ top: 8, right: 4, left: -16, bottom: 0 }}>
            <CartesianGrid stroke={palette.grid} strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey="date" tick={{ fontSize: 11, fill: palette.tick }} stroke={palette.axis} minTickGap={22} />
            <YAxis tick={{ fontSize: 11, fill: palette.tick }} stroke={palette.axis} width={54} unit="%" />
            <Tooltip
              contentStyle={palette.tooltip}
              formatter={(value, name) => [`${Number(value).toFixed(2)}%`, name]}
            />
            {tickers.map((ticker, index) => (
              <Line
                key={ticker}
                type="monotone"
                dataKey={ticker}
                stroke={COLORS[index % COLORS.length]}
                strokeWidth={2}
                dot={makeEndDot(merged.length, COLORS[index % COLORS.length])}
                activeDot={{ r: 4 }}
                connectNulls
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
