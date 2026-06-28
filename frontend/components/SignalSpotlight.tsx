"use client";

import { useMemo } from "react";
import Link from "next/link";
import { ArrowDownRight, ArrowUpRight } from "lucide-react";
import type { HoldingChange } from "@/lib/types";

// A안: "오늘의 기관 매매" 히어로.
// 브로커리지 앱이 '내 잔고'를 띄우는 자리에, Quantbot은 추적 ETF 전체에서
// shares가 가장 크게 움직인 매매(=기관의 의사결정)를 주인공으로 세운다.
// 판정 지표는 항상 shares_delta(주식수 변화) — weight는 가격에 흔들리므로 쓰지 않는다.

type SignalGroups = {
  spotlight: HoldingChange | null;
  buys: HoldingChange[];
  sells: HoldingChange[];
  asOf: string | null;
};

function buildGroups(changes: HoldingChange[]): SignalGroups {
  const withDelta = changes.filter(
    (change): change is HoldingChange & { shares_delta: number } =>
      change.shares_delta !== null && change.shares_delta !== 0
  );

  const buys = withDelta
    .filter((change) => change.shares_delta > 0)
    .sort((a, b) => b.shares_delta - a.shares_delta);
  const sells = withDelta
    .filter((change) => change.shares_delta < 0)
    .sort((a, b) => a.shares_delta - b.shares_delta);

  // |Δshares| 최대 1건을 spotlight로. 매수/매도 어느 쪽이든 가장 큰 결정을 띄운다.
  const spotlight =
    withDelta
      .slice()
      .sort((a, b) => Math.abs(b.shares_delta) - Math.abs(a.shares_delta))[0] ?? null;

  const asOf = changes.reduce<string | null>(
    (latest, change) => (latest === null || change.as_of_date > latest ? change.as_of_date : latest),
    null
  );

  return { spotlight, buys: buys.slice(0, 3), sells: sells.slice(0, 3), asOf };
}

function formatShares(value: number) {
  const rounded = Math.round(value);
  return `${rounded > 0 ? "+" : ""}${rounded.toLocaleString()}`;
}

export function SignalSpotlight({ changes }: { changes: HoldingChange[] }) {
  const { spotlight, buys, sells, asOf } = useMemo(() => buildGroups(changes), [changes]);

  if (!spotlight || spotlight.shares_delta === null) {
    return null;
  }

  const isBuy = spotlight.shares_delta > 0;
  const tone = isBuy
    ? {
        label: "최대 매수",
        text: "text-rise",
        chip: "bg-rise/10 text-rise ring-rise/15",
        dot: "bg-rise",
        surface: "from-rise/[0.07] to-transparent",
        Icon: ArrowUpRight,
        caption: "가장 많이 담은 종목"
      }
    : {
        label: "최대 매도",
        text: "text-fall",
        chip: "bg-fall/10 text-fall ring-fall/15",
        dot: "bg-fall",
        surface: "from-fall/[0.07] to-transparent",
        Icon: ArrowDownRight,
        caption: "가장 많이 덜어낸 종목"
      };

  return (
    <section
      className="rounded-xl border border-line bg-surface p-4 shadow-soft"
      aria-label="오늘의 주목 매매"
    >
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wide text-faint">
          오늘의 주목 매매
        </span>
        {asOf ? (
          <time className="text-xs font-medium tabular-nums text-faint" dateTime={asOf}>
            {asOf}
          </time>
        ) : null}
      </div>

      {/* 히어로: |Δshares| 최대 1건 */}
      <Link
        href={`/etfs/${spotlight.ticker}`}
        className={`mt-3 block rounded-lg bg-gradient-to-br ${tone.surface} p-4 ring-1 ring-inset ring-line transition hover:ring-line-strong`}
      >
        <div className="flex items-center gap-2">
          <span
            className={`inline-flex h-6 items-center gap-1.5 rounded-full px-2.5 text-xs font-semibold ring-1 ${tone.chip}`}
          >
            <tone.Icon className="h-3.5 w-3.5" aria-hidden="true" />
            {tone.label}
          </span>
          <span className="truncate text-xs font-medium text-muted">
            {spotlight.ticker} · {tone.caption}
          </span>
        </div>

        <div className="mt-3 flex items-end justify-between gap-3">
          <div className="min-w-0">
            <div className="truncate text-2xl font-bold leading-none tracking-tight text-ink">
              {spotlight.holding_ticker ?? "미상"}
            </div>
            <p className="mt-1.5 truncate text-sm text-muted">{spotlight.holding_name}</p>
          </div>
          <div className="shrink-0 text-right">
            <div className="text-[11px] text-faint">주식수 변화</div>
            <div className={`text-2xl font-bold leading-none tabular-nums ${tone.text}`}>
              {formatShares(spotlight.shares_delta)}
            </div>
          </div>
        </div>
      </Link>

      {/* 매수/매도 Top 미니 리스트 */}
      <div className="mt-3 grid grid-cols-2 gap-2">
        <SignalColumn title="매수 신호" accent="text-rise" dot="bg-rise" items={buys} />
        <SignalColumn title="매도 신호" accent="text-fall" dot="bg-fall" items={sells} />
      </div>
    </section>
  );
}

function SignalColumn({
  title,
  accent,
  dot,
  items
}: {
  title: string;
  accent: string;
  dot: string;
  items: HoldingChange[];
}) {
  return (
    <div className="rounded-lg border border-hair bg-panel p-3">
      <div className="flex items-center gap-1.5">
        <span className={`h-1.5 w-1.5 rounded-full ${dot}`} aria-hidden="true" />
        <span className="text-[11px] font-semibold text-faint">{title}</span>
      </div>
      <ul className="mt-2 space-y-1.5">
        {items.length === 0 ? (
          <li className="text-xs text-faint">없음</li>
        ) : (
          items.map((item) => (
            <li
              key={`${item.ticker}-${item.as_of_date}-${item.holding_ticker}-${item.holding_name}`}
              className="flex items-baseline justify-between gap-2"
            >
              <Link
                href={`/etfs/${item.ticker}`}
                className="truncate text-xs font-semibold text-body hover:text-brand"
                title={item.holding_name}
              >
                {item.holding_ticker ?? item.holding_name}
              </Link>
              <span className={`shrink-0 text-xs font-semibold tabular-nums ${accent}`}>
                {item.shares_delta === null ? "-" : formatShares(item.shares_delta)}
              </span>
            </li>
          ))
        )}
      </ul>
    </div>
  );
}
