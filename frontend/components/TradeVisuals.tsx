"use client";

import { ArrowDownRight, ArrowUpRight, Minus } from "lucide-react";
import type { ChangeType } from "@/lib/types";

type BadgeTone = {
  label: string;
  className: string;
  dot: string;
};

// 색 관습(데이터 콘솔: 옅은 틴트 + 같은 색 글씨). 신규=그린, 증가=빨강, 감소=파랑, 청산=중립 그레이.
const BADGE_TONES: Record<ChangeType, BadgeTone> = {
  NEW: {
    label: "신규",
    className: "bg-lime text-gain ring-gain/15",
    dot: "bg-gain"
  },
  EXIT: {
    label: "청산",
    className: "bg-ink/[0.06] text-ink ring-ink/10",
    dot: "bg-ink/40"
  },
  INCREASE: {
    label: "증가",
    className: "bg-rise/10 text-rise ring-rise/15",
    dot: "bg-rise"
  },
  DECREASE: {
    label: "감소",
    className: "bg-fall/10 text-fall ring-fall/15",
    dot: "bg-fall"
  },
  UNCHANGED: {
    label: "유지",
    className: "bg-panel text-muted ring-line",
    dot: "bg-muted/50"
  }
};

// 타임라인/마커용 점 색 (단일 출처). 신규=그린, 매수=빨강, 매도/청산=파랑, 유지=회색.
export const CHANGE_DOT: Record<ChangeType, string> = {
  NEW: "bg-gain",
  INCREASE: "bg-rise",
  DECREASE: "bg-fall",
  EXIT: "bg-ink/40",
  UNCHANGED: "bg-muted/50"
};

export function ChangeBadge({
  type,
  compact = false
}: {
  type: ChangeType | null;
  compact?: boolean;
}) {
  if (!type) {
    return <span className="text-xs text-muted">-</span>;
  }

  const tone = BADGE_TONES[type];

  return (
    <span
      className={`inline-flex h-6 shrink-0 items-center justify-center gap-1.5 whitespace-nowrap rounded-full px-2.5 text-xs font-medium leading-none ring-1 ${tone.className} ${
        compact ? "min-w-[52px]" : "min-w-[58px]"
      }`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${tone.dot}`} aria-hidden="true" />
      {tone.label}
    </span>
  );
}

export function DeltaValue({ value, suffix }: { value: number | null; suffix: string }) {
  if (value === null) {
    return <span className="text-muted">-</span>;
  }

  const isPositive = value > 0;
  const isNegative = value < 0;
  const className = isPositive ? "text-rise" : isNegative ? "text-fall" : "text-muted";
  const Icon = isPositive ? ArrowUpRight : isNegative ? ArrowDownRight : Minus;
  const decimals = suffix === "%" ? 2 : Number.isInteger(value) ? 0 : 4;
  const formatted = value.toLocaleString(undefined, {
    maximumFractionDigits: decimals,
    minimumFractionDigits: decimals
  });

  return (
    <span className={`inline-flex items-center justify-end gap-1 whitespace-nowrap font-semibold tabular-nums ${className}`}>
      <Icon className="h-3.5 w-3.5" aria-hidden="true" />
      <span>
        {isPositive ? "+" : ""}
        {formatted}
        {suffix}
      </span>
    </span>
  );
}
