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
  return (
    <div className="h-[300px] rounded-lg border border-line bg-white p-4 shadow-soft">
      <div className="mb-3 text-sm font-semibold text-ink">{label ? `${label} 포지션 추이` : "종목 선택"}</div>
      {isLoading ? (
        <div className="flex h-[240px] items-center justify-center text-sm text-muted">불러오는 중</div>
      ) : points.length === 0 ? (
        <div className="flex h-[240px] items-center justify-center text-sm text-muted">
          추세 데이터 없음
        </div>
      ) : (
        <ResponsiveContainer width="100%" height="85%">
          <LineChart data={points} margin={{ top: 8, right: 18, left: 0, bottom: 8 }}>
            <CartesianGrid stroke="#d7dee8" strokeDasharray="3 3" />
            <XAxis dataKey="as_of_date" tick={{ fontSize: 12 }} minTickGap={28} />
            <YAxis yAxisId="shares" tick={{ fontSize: 12 }} width={70} />
            <YAxis yAxisId="weight" orientation="right" tick={{ fontSize: 12 }} width={52} unit="%" />
            <Tooltip
              formatter={(value, name) => [
                name === "비중" ? `${Number(value).toFixed(2)}%` : Number(value).toLocaleString(),
                name
              ]}
            />
            <Line
              yAxisId="shares"
              type="monotone"
              dataKey="shares"
              name="주식수"
              stroke="#2563eb"
              strokeWidth={2}
              dot={false}
            />
            <Line
              yAxisId="weight"
              type="monotone"
              dataKey="weight"
              name="비중"
              stroke="#0f766e"
              strokeWidth={2}
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
