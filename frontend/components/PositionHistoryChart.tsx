"use client";

import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";
import { AreaGradient, fillId, makeEndDot } from "@/components/chartHelpers";
import { ChartSkeleton } from "@/components/Skeleton";
import { useChartPalette } from "@/components/ThemeProvider";
import type { PositionHistoryPoint } from "@/lib/types";

export function PositionHistoryChart({
  points,
  label,
  isLoading
}: {
  points: PositionHistoryPoint[];
  label: string | null;
  isLoading?: boolean;
}) {
  const palette = useChartPalette();
  return (
    <div className="rounded-lg border border-line bg-surface p-4">
      <div className="mb-3 text-sm font-semibold text-ink">
        {label ? `${label} 포지션 추이` : "종목 선택"}
      </div>
      {isLoading ? (
        <ChartSkeleton height={240} />
      ) : points.length === 0 ? (
        <div className="flex h-[240px] items-center justify-center text-sm text-muted">
          추세 데이터 없음
        </div>
      ) : (
        <div className="h-[240px]">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={points} margin={{ top: 8, right: 6, left: -16, bottom: 0 }}>
              <defs>
                <AreaGradient id={fillId("position-shares")} color={palette.line} />
              </defs>
              <CartesianGrid stroke={palette.grid} strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="as_of_date" tick={{ fontSize: 11, fill: palette.tick }} stroke={palette.axis} minTickGap={22} />
              <YAxis yAxisId="shares" tick={{ fontSize: 11, fill: palette.tick }} stroke={palette.axis} width={64} />
              <YAxis yAxisId="weight" orientation="right" tick={{ fontSize: 11, fill: palette.tick }} stroke={palette.axis} width={44} unit="%" />
              <Tooltip
                contentStyle={palette.tooltip}
                formatter={(value, name) => [
                  name === "비중" ? `${Number(value).toFixed(2)}%` : Number(value).toLocaleString(),
                  name
                ]}
              />
              <Area
                yAxisId="shares"
                type="monotone"
                dataKey="shares"
                name="주식수"
                stroke={palette.line}
                strokeWidth={2}
                fill={`url(#${fillId("position-shares")})`}
                dot={makeEndDot(points.length, palette.line)}
                activeDot={{ r: 4 }}
              />
              <Line
                yAxisId="weight"
                type="monotone"
                dataKey="weight"
                name="비중"
                stroke="#0d9488"
                strokeWidth={2}
                dot={false}
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
