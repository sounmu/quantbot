"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { ChangeBadge, CHANGE_DOT, DeltaValue } from "@/components/TradeVisuals";
import { CardSkeletonList } from "@/components/Skeleton";
import type { HoldingChange } from "@/lib/types";

type Props = {
  changes: HoldingChange[];
  showEtf?: boolean;
  isLoading?: boolean;
  errorMessage?: string;
  initialVisibleCount?: number;
  visibleStep?: number;
};

export function ChangeFeed({
  changes,
  showEtf = false,
  isLoading,
  errorMessage,
  initialVisibleCount,
  visibleStep = initialVisibleCount ?? 10
}: Props) {
  const [visibleCount, setVisibleCount] = useState(initialVisibleCount ?? changes.length);
  const visibleChanges = useMemo(
    () => changes.slice(0, Math.min(visibleCount, changes.length)),
    [changes, visibleCount]
  );
  const remainingCount = Math.max(0, changes.length - visibleChanges.length);

  useEffect(() => {
    setVisibleCount(initialVisibleCount ?? changes.length);
  }, [changes, initialVisibleCount]);

  return (
    <section className="space-y-3" aria-label={showEtf ? "최근 매매 피드" : "스냅샷 변동 피드"}>
      {errorMessage ? (
        <StatusCard tone="error">{errorMessage}</StatusCard>
      ) : isLoading ? (
        <CardSkeletonList count={5} metrics={2} />
      ) : changes.length === 0 ? (
        <StatusCard>변동 데이터 없음</StatusCard>
      ) : (
        <>
          <ol className="relative space-y-3 border-l border-line pl-4">
            {visibleChanges.map((change) => (
              <li
                key={`${change.ticker}-${change.as_of_date}-${change.holding_ticker}-${change.holding_name}`}
                className="relative"
              >
                <span
                  className={`absolute -left-[21px] top-5 h-3 w-3 rounded-full border-2 border-surface ${
                    CHANGE_DOT[change.change_type] ?? "bg-muted/50"
                  }`}
                />
                <article className="rounded-lg border border-line bg-surface p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        {showEtf ? (
                          <Link
                            className="rounded text-xs font-semibold text-cobalt"
                            href={`/etfs/${change.ticker}`}
                          >
                            {change.ticker}
                          </Link>
                        ) : null}
                        <ChangeBadge type={change.change_type} />
                      </div>
                      <h2 className="mt-2 text-lg font-bold leading-none tracking-tight text-ink">
                        {change.holding_ticker ?? "N/A"}
                      </h2>
                      <p className="mt-2 break-words text-sm leading-snug text-muted">
                        {change.holding_name}
                      </p>
                    </div>
                    <time className="shrink-0 text-xs font-medium tabular-nums text-faint" dateTime={change.as_of_date}>
                      {change.as_of_date}
                    </time>
                  </div>

                  <div className="mt-4 grid grid-cols-2 gap-2 border-t border-hair pt-3 text-xs">
                    <Metric label="주식수 Δ" value={<DeltaValue value={change.shares_delta} suffix="" />} />
                    <Metric label="비중 Δ" value={<DeltaValue value={change.weight_delta} suffix="%" />} />
                  </div>
                </article>
              </li>
            ))}
          </ol>

          {remainingCount > 0 ? (
            <button
              className="min-h-11 w-full rounded-lg border border-line bg-surface px-4 text-sm font-semibold text-body transition hover:border-brand/40 hover:text-brand"
              type="button"
              onClick={() => setVisibleCount((current) => Math.min(changes.length, current + visibleStep))}
            >
              더보기 {remainingCount.toLocaleString()}개
            </button>
          ) : null}
        </>
      )}
    </section>
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
