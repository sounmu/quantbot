"use client";

import { ArrowDownRight, ArrowUpRight, Minus } from "lucide-react";
import type {
  ActiveConfidence,
  ActiveDirection,
  ActiveIntensity,
  ChangeType,
  FlowAdjusted
} from "@/lib/types";

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

const NEUTRAL_FLOW_TONE: BadgeTone = {
    label: "자금 동반",
    className: "bg-panel text-muted ring-line",
    dot: "bg-muted/50"
};

const ACTIVE_CONFIDENCE_LABELS: Record<ActiveConfidence, string> = {
  LOW: "낮음",
  MEDIUM: "보통",
  HIGH: "높음"
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

// 교차 시그널 배지: 같은 날 같은 종목을 매매한 시그널 ETF 수(매수/매도).
// 나 혼자만의 베팅인지, 여러 운용사의 컨센서스인지를 한눈에 구분한다.
export function CrossSignalBadge({
  buying,
  selling
}: {
  buying: number | null;
  selling: number | null;
}) {
  const buy = buying ?? 0;
  const sell = selling ?? 0;
  if (buy === 0 && sell === 0) {
    return <span className="text-xs text-muted">-</span>;
  }

  // 매수·매도 ETF 수 차이가 2 이상이면 여러 운용사가 한 방향에 동의한 컨센서스로 강조.
  // (정적 클래스로 분기 — Tailwind JIT가 동적 템플릿 클래스를 purge하기 때문.)
  const consensus = Math.abs(buy - sell) >= 2;
  const consensusClass =
    buy >= sell ? "bg-rise/10 text-rise ring-rise/15" : "bg-fall/10 text-fall ring-fall/15";

  return (
    <span
      className={`inline-flex h-6 items-center gap-1.5 whitespace-nowrap rounded-full px-2.5 text-xs font-medium leading-none ring-1 ${
        consensus ? consensusClass : "bg-panel text-muted ring-line"
      }`}
      title="같은 날 이 종목을 매매한 시그널 ETF 수 (매수 / 매도)"
    >
      {buy > 0 ? (
        <span className="inline-flex items-center gap-0.5 tabular-nums text-rise">
          <ArrowUpRight className="h-3 w-3" aria-hidden="true" />
          {buy}
        </span>
      ) : null}
      {sell > 0 ? (
        <span className="inline-flex items-center gap-0.5 tabular-nums text-fall">
          <ArrowDownRight className="h-3 w-3" aria-hidden="true" />
          {sell}
        </span>
      ) : null}
    </span>
  );
}

export function ActiveSignalBadge({
  direction,
  intensity,
  confidence,
  residualNavBp,
  residualPositionPct,
  fallback,
  compact = false
}: {
  direction: ActiveDirection | null;
  intensity: ActiveIntensity | null;
  confidence?: ActiveConfidence | null;
  residualNavBp?: number | null;
  residualPositionPct?: number | null;
  fallback?: FlowAdjusted | null;
  compact?: boolean;
}) {
  const normalized = signalTone(direction, intensity, fallback);
  if (!normalized) {
    return <span className="text-xs text-muted">-</span>;
  }

  const { tone, active } = normalized;

  return (
    <span
      className={`inline-flex h-6 shrink-0 items-center justify-center gap-1.5 whitespace-nowrap rounded-full px-2.5 text-xs font-medium leading-none ring-1 ${tone.className} ${
        compact ? "min-w-[84px]" : "min-w-[98px]"
      }`}
      title={activeSignalTitle(active, confidence, residualNavBp, residualPositionPct)}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${tone.dot}`} aria-hidden="true" />
      {tone.label}
    </span>
  );
}

export function FlowAdjustedBadge({
  type,
  compact = false
}: {
  type: FlowAdjusted | null;
  compact?: boolean;
}) {
  return <ActiveSignalBadge direction={null} intensity={null} fallback={type} compact={compact} />;
}

function signalTone(
  direction: ActiveDirection | null,
  intensity: ActiveIntensity | null,
  fallback?: FlowAdjusted | null
): { tone: BadgeTone; active: { direction: ActiveDirection; intensity: ActiveIntensity } } | null {
  const resolved = resolveActiveSignal(direction, intensity, fallback);
  if (!resolved) return null;
  if (resolved.direction === "NEUTRAL" || resolved.intensity === "NONE") {
    return { tone: NEUTRAL_FLOW_TONE, active: resolved };
  }

  const buy = resolved.direction === "BUY";
  const className = buy ? "bg-rise/10 text-rise ring-rise/15" : "bg-fall/10 text-fall ring-fall/15";
  const dot = buy ? "bg-rise" : "bg-fall";
  const label = activeSignalLabel(resolved.direction, resolved.intensity);
  return { tone: { label, className, dot }, active: resolved };
}

function resolveActiveSignal(
  direction: ActiveDirection | null,
  intensity: ActiveIntensity | null,
  fallback?: FlowAdjusted | null
): { direction: ActiveDirection; intensity: ActiveIntensity } | null {
  if (direction && intensity) {
    return { direction, intensity };
  }
  if (!fallback) return null;
  if (fallback === "HOLD") {
    return { direction: "NEUTRAL", intensity: "NONE" };
  }
  return { direction: fallback, intensity: "MEDIUM" };
}

function activeSignalLabel(direction: ActiveDirection, intensity: ActiveIntensity) {
  if (direction === "NEUTRAL" || intensity === "NONE") return "자금 동반";
  if (direction === "BUY") {
    if (intensity === "STRONG") return "강한 능동 매수";
    if (intensity === "WEAK") return "약한 매수 기울기";
    return "능동 매수";
  }
  if (intensity === "STRONG") return "강한 능동 매도";
  if (intensity === "WEAK") return "약한 매도 기울기";
  return "능동 매도";
}

function activeSignalTitle(
  active: { direction: ActiveDirection; intensity: ActiveIntensity },
  confidence?: ActiveConfidence | null,
  residualNavBp?: number | null,
  residualPositionPct?: number | null
) {
  const parts = ["ETF 자금 유입/유출 추정치를 뺀 뒤의 주식수 잔차 기준"];
  parts.push(`강도: ${active.intensity}`);
  if (confidence) parts.push(`신뢰도: ${ACTIVE_CONFIDENCE_LABELS[confidence]}`);
  if (typeof residualNavBp === "number") parts.push(`NAV 잔차: ${residualNavBp.toFixed(2)}bp`);
  if (typeof residualPositionPct === "number") {
    parts.push(`포지션 잔차: ${(residualPositionPct * 100).toFixed(2)}%`);
  }
  return parts.join(" · ");
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
