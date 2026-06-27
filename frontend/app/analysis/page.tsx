"use client";

import Link from "next/link";
import { useMemo } from "react";
import { AppShell } from "@/components/AppShell";
import { CardSkeletonList } from "@/components/Skeleton";
import { SignalSpotlight } from "@/components/SignalSpotlight";
import { ChangeBadge, DeltaValue } from "@/components/TradeVisuals";
import { useRecentChanges } from "@/hooks/useRecentChanges";
import type { HoldingChange } from "@/lib/types";

export default function AnalysisPage() {
  const recentChanges = useRecentChanges(200);
  const buySignals = useMemo(
    () =>
      (recentChanges.data ?? [])
        .filter((change) => change.change_type === "NEW" || change.change_type === "INCREASE")
        .sort((a, b) => Math.abs(b.weight_delta ?? 0) - Math.abs(a.weight_delta ?? 0))
        .slice(0, 25),
    [recentChanges.data]
  );

  return (
    <AppShell>
      <div className="mb-5">
        <h1 className="text-2xl font-bold leading-tight tracking-tight text-ink">분석</h1>
        <p className="mt-2 text-sm leading-snug text-muted">
          최근 공시에서 shares가 늘어난 보유종목입니다.
        </p>
      </div>

      {recentChanges.isError ? (
        <StatusCard tone="error">분석 데이터를 불러오지 못했습니다.</StatusCard>
      ) : recentChanges.isLoading ? (
        <div className="space-y-5">
          <CardSkeletonList count={1} metrics={2} />
          <CardSkeletonList count={4} metrics={2} />
        </div>
      ) : (
        <div className="space-y-5">
          <SignalSpotlight changes={recentChanges.data ?? []} />

          <section className="space-y-3" aria-label="shares 증가 신호">
            <h2 className="text-sm font-semibold text-ink">shares 증가 종목</h2>
            {buySignals.length === 0 ? (
              <StatusCard>shares 증가 신호 없음</StatusCard>
            ) : (
              buySignals.map((signal) => <SignalCard key={signalKey(signal)} signal={signal} />)
            )}
          </section>
        </div>
      )}
    </AppShell>
  );
}

function SignalCard({ signal }: { signal: HoldingChange }) {
  return (
    <article className="rounded-lg border border-line bg-surface p-4 transition hover:border-line-strong">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <Link className="rounded text-xs font-semibold text-cobalt" href={`/etfs/${signal.ticker}`}>
              {signal.ticker}
            </Link>
            <ChangeBadge type={signal.change_type} />
          </div>
          <h2 className="mt-2 text-lg font-bold leading-none tracking-tight text-ink">
            {signal.holding_ticker ?? "N/A"}
          </h2>
          <p className="mt-2 break-words text-sm leading-snug text-muted">{signal.holding_name}</p>
        </div>
        <time className="shrink-0 text-xs font-medium tabular-nums text-faint" dateTime={signal.as_of_date}>
          {signal.as_of_date}
        </time>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-2 border-t border-hair pt-3 text-xs">
        <Metric label="주식수 Δ" value={<DeltaValue value={signal.shares_delta} suffix="" />} />
        <Metric label="비중 Δ" value={<DeltaValue value={signal.weight_delta} suffix="%" />} />
      </div>
    </article>
  );
}

function StatusCard({ children, tone = "muted" }: { children: React.ReactNode; tone?: "muted" | "error" }) {
  return (
    <div
      className={`rounded-lg border border-line bg-surface px-4 py-10 text-center text-sm ${
        tone === "error" ? "text-rise" : "text-muted"
      }`}
    >
      {children}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="min-w-0">
      <div className="text-[11px] text-faint">{label}</div>
      <div className="mt-1 truncate text-sm font-semibold tabular-nums text-ink">{value}</div>
    </div>
  );
}

function signalKey(signal: HoldingChange) {
  return `${signal.ticker}-${signal.as_of_date}-${signal.holding_ticker}-${signal.holding_name}`;
}
