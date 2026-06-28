"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { ChangeBadge, DeltaValue } from "@/components/TradeVisuals";
import { CardSkeletonList } from "@/components/Skeleton";
import type { HoldingChange } from "@/lib/types";

type Props = {
  changes: HoldingChange[];
  showEtf?: boolean;
  isLoading?: boolean;
  errorMessage?: string;
  initialVisibleCount?: number;
  visibleStep?: number;
  // 좁은 사이드 컬럼용: 데스크탑에서도 테이블 대신 타임라인 카드만 사용한다.
  dense?: boolean;
};

export function ChangeFeed({
  changes,
  showEtf = false,
  isLoading,
  errorMessage,
  initialVisibleCount,
  visibleStep = initialVisibleCount ?? 10,
  dense = false
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
    <section className="space-y-3" aria-label={showEtf ? "최근 매매 내역" : "기준일 변동 내역"}>
      {errorMessage ? (
        <StatusCard tone="error">{errorMessage}</StatusCard>
      ) : isLoading ? (
        <CardSkeletonList count={5} metrics={2} />
      ) : changes.length === 0 ? (
        <StatusCard>변동 데이터 없음</StatusCard>
      ) : (
        <>
          {/* 모바일(+dense 사이드 컬럼): 타임라인 카드 */}
          <ol className={`space-y-3 ${dense ? "" : "lg:hidden"}`}>
            {visibleChanges.map((change) => (
              <li
                key={`${change.ticker}-${change.as_of_date}-${change.holding_ticker}-${change.holding_name}`}
              >
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
                        {change.holding_ticker ?? "미상"}
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
                    <Metric label="주식수 변화" value={<DeltaValue value={change.shares_delta} suffix="" />} />
                    <Metric label="비중 변화" value={<DeltaValue value={change.weight_delta} suffix="%" />} />
                  </div>
                </article>
              </li>
            ))}
          </ol>

          {/* 데스크탑: 테이블 (dense 모드에서는 렌더하지 않음) */}
          {!dense && (
          <div className="hidden overflow-hidden rounded-lg border border-line bg-surface lg:block">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-line text-left text-xs font-semibold text-faint">
                  {showEtf ? <th className="px-3 py-2.5 pl-4">ETF</th> : null}
                  <th className={`px-3 py-2.5 ${showEtf ? "" : "pl-4"}`}>종목</th>
                  <th className="px-3 py-2.5">이름</th>
                  <th className="px-3 py-2.5">변동</th>
                  <th className="px-3 py-2.5 text-right">주식수 변화</th>
                  <th className="px-3 py-2.5 text-right">비중 변화</th>
                  <th className="px-3 py-2.5 pr-4 text-right">날짜</th>
                </tr>
              </thead>
              <tbody>
                {visibleChanges.map((change) => (
                  <tr
                    key={`${change.ticker}-${change.as_of_date}-${change.holding_ticker}-${change.holding_name}`}
                    className="border-b border-hair last:border-0 transition hover:bg-panel"
                  >
                    {showEtf ? (
                      <td className="py-3 pl-4">
                        <Link className="font-semibold text-cobalt hover:text-brand" href={`/etfs/${change.ticker}`}>
                          {change.ticker}
                        </Link>
                      </td>
                    ) : null}
                    <td className={`py-3 font-bold tracking-tight text-ink ${showEtf ? "pr-3" : "pl-4 pr-3"}`}>
                      {change.holding_ticker ?? "미상"}
                    </td>
                    <td className="max-w-[280px] truncate py-3 pr-3 text-muted" title={change.holding_name}>
                      {change.holding_name}
                    </td>
                    <td className="py-3 pr-3">
                      <ChangeBadge type={change.change_type} />
                    </td>
                    <td className="py-3 pr-3 text-right tabular-nums">
                      <DeltaValue value={change.shares_delta} suffix="" />
                    </td>
                    <td className="py-3 pr-3 text-right tabular-nums">
                      <DeltaValue value={change.weight_delta} suffix="%" />
                    </td>
                    <td className="py-3 pr-4 text-right text-xs tabular-nums text-faint">
                      <time dateTime={change.as_of_date}>{change.as_of_date}</time>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          )}

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
