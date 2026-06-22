"use client";

import { useMemo, useState } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";
import type { PricePoint } from "@/lib/types";

type ChartMode = "price" | "return";
type MovingAverageKey = "ma20" | "ma50" | "ma200";

const MOVING_AVERAGES: Array<{
  key: MovingAverageKey;
  label: string;
  period: number;
  color: string;
}> = [
  { key: "ma20", label: "MA20", period: 20, color: "#0f766e" },
  { key: "ma50", label: "MA50", period: 50, color: "#be185d" },
  { key: "ma200", label: "MA200", period: 200, color: "#ea580c" }
];

export function PriceChart({ prices }: { prices: PricePoint[] }) {
  const [mode, setMode] = useState<ChartMode>("price");
  const [enabledAverages, setEnabledAverages] = useState<MovingAverageKey[]>(["ma20", "ma50"]);
  const chartData = useMemo(() => enrichPrices(prices), [prices]);
  const primaryKey = mode === "price" ? "close" : "closeReturn";

  return (
    <div className="rounded-lg border border-line bg-white p-4 shadow-soft">
      <div className="mb-4 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex w-fit rounded-md border border-line bg-panel p-1">
          <button
            className={`h-8 rounded px-3 text-xs font-medium ${
              mode === "price" ? "bg-ink text-white" : "text-muted hover:bg-white"
            }`}
            onClick={() => setMode("price")}
          >
            가격
          </button>
          <button
            className={`h-8 rounded px-3 text-xs font-medium ${
              mode === "return" ? "bg-ink text-white" : "text-muted hover:bg-white"
            }`}
            onClick={() => setMode("return")}
          >
            수익률
          </button>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {MOVING_AVERAGES.map((average) => (
            <label
              key={average.key}
              className="inline-flex h-8 items-center gap-2 rounded-md border border-line bg-white px-3 text-xs font-medium text-ink"
            >
              <input
                className="h-3.5 w-3.5 accent-accent"
                type="checkbox"
                checked={enabledAverages.includes(average.key)}
                onChange={() => {
                  setEnabledAverages((current) =>
                    current.includes(average.key)
                      ? current.filter((item) => item !== average.key)
                      : [...current, average.key]
                  );
                }}
              />
              <span style={{ color: average.color }}>{average.label}</span>
            </label>
          ))}
        </div>
      </div>

      {chartData.length === 0 ? (
        <div className="flex h-[320px] items-center justify-center text-sm text-muted">
          가격 데이터 없음
        </div>
      ) : (
        <div className="h-[320px]">
          <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData} margin={{ top: 8, right: 18, left: 0, bottom: 8 }}>
              <CartesianGrid stroke="#d7dee8" strokeDasharray="3 3" />
              <XAxis dataKey="date" tick={{ fontSize: 12 }} minTickGap={28} />
              <YAxis
                tick={{ fontSize: 12 }}
                domain={["auto", "auto"]}
                unit={mode === "return" ? "%" : undefined}
                width={58}
              />
              <Tooltip
                formatter={(value, name) => [
                  formatTooltip(value === null ? null : Number(value), mode),
                  String(name)
                ]}
              />
              <Line
                type="monotone"
                dataKey={primaryKey}
                name={mode === "price" ? "종가" : "수익률"}
                stroke="#2563eb"
                strokeWidth={2}
                dot={false}
              />
              {MOVING_AVERAGES.filter((average) => enabledAverages.includes(average.key)).map(
                (average) => (
                  <Line
                    key={average.key}
                    type="monotone"
                    dataKey={mode === "price" ? average.key : `${average.key}Return`}
                    name={average.label}
                    stroke={average.color}
                    strokeWidth={1.6}
                    dot={false}
                    connectNulls={false}
                  />
                )
              )}
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}

type EnrichedPricePoint = PricePoint & {
  closeReturn: number;
  ma20: number | null;
  ma50: number | null;
  ma200: number | null;
  ma20Return: number | null;
  ma50Return: number | null;
  ma200Return: number | null;
};

function enrichPrices(prices: PricePoint[]): EnrichedPricePoint[] {
  if (prices.length === 0) {
    return [];
  }

  const baseline = prices[0].close;
  return prices.map((point, index) => {
    const ma20 = movingAverage(prices, index, 20);
    const ma50 = movingAverage(prices, index, 50);
    const ma200 = movingAverage(prices, index, 200);

    return {
      ...point,
      closeReturn: percentReturn(point.close, baseline),
      ma20,
      ma50,
      ma200,
      ma20Return: ma20 === null ? null : percentReturn(ma20, baseline),
      ma50Return: ma50 === null ? null : percentReturn(ma50, baseline),
      ma200Return: ma200 === null ? null : percentReturn(ma200, baseline)
    };
  });
}

function movingAverage(prices: PricePoint[], index: number, period: number) {
  if (index + 1 < period) {
    return null;
  }

  const window = prices.slice(index + 1 - period, index + 1);
  const total = window.reduce((sum, point) => sum + point.close, 0);
  return Number((total / period).toFixed(4));
}

function percentReturn(value: number, baseline: number) {
  if (baseline <= 0) {
    return 0;
  }
  return Number((((value / baseline) - 1) * 100).toFixed(4));
}

function formatTooltip(value: number | null, mode: ChartMode) {
  if (value === null) {
    return "-";
  }
  return mode === "price" ? `$${value.toFixed(2)}` : `${value.toFixed(2)}%`;
}
