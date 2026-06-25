"use client";

import { ArrowDownRight, ArrowUpRight, Minus } from "lucide-react";
import type { ChangeType } from "@/lib/types";

type BadgeTone = {
  label: string;
  className: string;
  dot: string;
};

const BADGE_TONES: Record<ChangeType, BadgeTone> = {
  NEW: {
    label: "신규",
    className: "bg-cobalt/10 text-cobalt ring-cobalt/15",
    dot: "bg-cobalt"
  },
  EXIT: {
    label: "청산",
    className: "bg-ink/[0.06] text-ink ring-ink/10",
    dot: "bg-ink"
  },
  INCREASE: {
    label: "증가",
    className: "bg-accent/10 text-accent ring-accent/15",
    dot: "bg-accent"
  },
  DECREASE: {
    label: "감소",
    className: "bg-berry/10 text-berry ring-berry/15",
    dot: "bg-berry"
  },
  UNCHANGED: {
    label: "유지",
    className: "bg-panel text-muted ring-line",
    dot: "bg-muted/50"
  }
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
  const className = isPositive ? "text-accent" : isNegative ? "text-berry" : "text-muted";
  const Icon = isPositive ? ArrowUpRight : isNegative ? ArrowDownRight : Minus;
  const decimals = suffix === "%" ? 2 : Number.isInteger(value) ? 0 : 4;
  const formatted = value.toLocaleString(undefined, {
    maximumFractionDigits: decimals,
    minimumFractionDigits: decimals
  });

  return (
    <span className={`inline-flex items-center justify-end gap-1 whitespace-nowrap font-medium ${className}`}>
      <Icon className="h-3.5 w-3.5" aria-hidden="true" />
      <span>
        {isPositive ? "+" : ""}
        {formatted}
        {suffix}
      </span>
    </span>
  );
}
