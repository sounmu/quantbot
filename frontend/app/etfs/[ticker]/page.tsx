"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft, Star } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { ChangeFeed } from "@/components/ChangeFeed";
import { HoldingsTable } from "@/components/HoldingsTable";
import { PositionHistoryChart } from "@/components/PositionHistoryChart";
import { PriceChart } from "@/components/PriceChart";
import { DeltaValue } from "@/components/TradeVisuals";
import {
  useEtfDetail,
  useEtfFlow,
  useEtfPrices,
  useHoldingChanges,
  useHoldingDates,
  useHoldings,
  usePositionHistory
} from "@/hooks/useEtfDetail";
import { useWatchlist } from "@/hooks/useWatchlist";
import type { EtfFlow } from "@/lib/types";
import { useEffect, useState } from "react";

const RANGES = ["1m", "3m", "6m", "1y", "ytd", "max"];

export default function EtfDetailPage() {
  const params = useParams<{ ticker: string }>();
  const ticker = String(params.ticker ?? "").toUpperCase();
  const [range, setRange] = useState("1y");
  const [snapshotDate, setSnapshotDate] = useState<string | undefined>();
  const [selectedPosition, setSelectedPosition] = useState<string | null>(null);
  const [selectedPositionLabel, setSelectedPositionLabel] = useState<string | null>(null);
  const detail = useEtfDetail(ticker);
  const prices = useEtfPrices(ticker, range);
  const flowSeries = useEtfFlow(ticker, "1y");
  const holdingDates = useHoldingDates(ticker);
  const holdings = useHoldings(ticker, snapshotDate);
  const holdingChanges = useHoldingChanges(ticker, snapshotDate);
  const positionHistory = usePositionHistory(ticker, selectedPosition);
  const watchlist = useWatchlist();
  const flowItems = flowSeries.data ?? [];
  const selectedFlow = snapshotDate
    ? flowItems.find((flow) => flow.as_of_date === snapshotDate) ?? null
    : flowItems[flowItems.length - 1] ?? null;

  useEffect(() => {
    setSnapshotDate(undefined);
    setSelectedPosition(null);
    setSelectedPositionLabel(null);
  }, [ticker]);

  useEffect(() => {
    if (!snapshotDate && holdingDates.data?.length) {
      setSnapshotDate(holdingDates.data[0]);
    }
  }, [holdingDates.data, snapshotDate]);

  useEffect(() => {
    if (!selectedPosition && holdings.data?.length) {
      const first = holdings.data[0];
      setSelectedPosition(first.holding_key ?? first.holding_ticker ?? nameKey(first.holding_name));
      setSelectedPositionLabel(first.holding_ticker ?? first.holding_name);
    }
  }, [holdings.data, selectedPosition]);

  return (
    <AppShell>
      <div className="mb-5">
        <Link className="inline-flex min-h-11 items-center gap-2 text-sm text-muted hover:text-ink" href="/etfs">
          <ArrowLeft className="h-4 w-4" aria-hidden="true" />
          목록
        </Link>
      </div>

      <section className="mb-6">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <h1 className="text-3xl font-bold leading-none tracking-tight text-ink">{ticker}</h1>
            <p className="mt-2 break-words text-sm leading-snug text-muted">
              {detail.data?.name ?? (detail.isLoading ? "불러오는 중" : "ETF 정보 없음")}
            </p>
          </div>
          <button
            className="inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-lg text-faint transition hover:bg-panel hover:text-berry"
            onClick={() => watchlist.toggle(ticker)}
            title="관심목록"
            aria-label={watchlist.has(ticker) ? "관심목록에서 제거" : "관심목록에 추가"}
            aria-pressed={watchlist.has(ticker)}
          >
            <Star
              className="h-5 w-5"
              fill={watchlist.has(ticker) ? "currentColor" : "none"}
              aria-hidden="true"
            />
          </button>
        </div>

        {detail.data ? (
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <SignalUniverseBadge
              inUniverse={detail.data.in_signal_universe}
              reason={detail.data.signal_universe_reason}
            />
          </div>
        ) : null}

        {/* 수익률 요약 */}
        <div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-4">
          <Stat label="1개월" value={<DeltaValue value={detail.data?.return_1m ?? null} suffix="%" />} />
          <Stat label="3개월" value={<DeltaValue value={detail.data?.return_3m ?? null} suffix="%" />} />
          <Stat label="연초이후" value={<DeltaValue value={detail.data?.return_ytd ?? null} suffix="%" />} />
          <Stat label="1년" value={<DeltaValue value={detail.data?.return_1y ?? null} suffix="%" />} />
        </div>

        {/* 기본 정보 */}
        <div className="mt-2 grid grid-cols-2 gap-2 text-sm sm:grid-cols-4">
          <Stat label="운용사" value={detail.data?.issuer ?? "-"} />
          <Stat label="테마" value={detail.data?.theme ?? "-"} />
          <Stat label="보수율" value={formatPercent(detail.data?.expense_ratio ?? null)} />
          <Stat label="자산규모" value={formatAum(detail.data?.aum ?? null)} />
          <Stat label="거래소" value={detail.data?.exchange ?? "-"} />
          <Stat label="설정일" value={detail.data?.inception_date ?? "-"} />
          <Stat label="통화" value={detail.data?.currency ?? "-"} />
          <Stat label="공시" value={detail.data?.discloses_daily ? "일별" : "미지원"} />
        </div>

        <FlowSummary
          flow={selectedFlow}
          snapshotDate={snapshotDate}
          isLoading={flowSeries.isLoading}
          isError={flowSeries.isError}
        />

        {detail.data?.description ? (
          <p className="mt-3 break-words text-sm leading-relaxed text-muted">
            {detail.data.description}
          </p>
        ) : null}
      </section>

      <div className="grid gap-6 xl:grid-cols-3 xl:items-start">
        {/* 좌측: 기준일 보유 현황 */}
        <div className="space-y-4 xl:col-span-2">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <h2 className="text-lg font-bold tracking-tight text-ink">기준일 보유 현황</h2>
              <p className="mt-1 text-sm text-muted">
                주식수 변화 기준으로 실제 매매 방향을 판정하고, 비중 변화는 보조 지표로 표시합니다.
              </p>
            </div>
            <select
              className="h-11 w-full rounded-lg border border-line bg-surface px-3 text-sm tabular-nums text-body sm:w-auto"
              value={snapshotDate ?? ""}
              onChange={(event) => {
                setSnapshotDate(event.target.value || undefined);
                setSelectedPosition(null);
                setSelectedPositionLabel(null);
              }}
            >
              {(holdingDates.data ?? []).map((date) => (
                <option key={date} value={date}>
                  {date}
                </option>
              ))}
            </select>
          </div>

          <PositionHistoryChart
            points={positionHistory.data ?? []}
            label={selectedPositionLabel}
            isLoading={positionHistory.isLoading}
          />
          <HoldingsTable
            holdings={holdings.data ?? []}
            isLoading={holdings.isLoading}
            errorMessage={holdings.isError ? "보유종목 데이터를 불러오지 못했습니다." : undefined}
            selectedKey={selectedPosition}
            onSelect={(key, label) => {
              setSelectedPosition(key);
              setSelectedPositionLabel(label);
            }}
          />
        </div>

        {/* 우측: 가격 흐름 + 기준일 변동 내역 */}
        <div className="space-y-6 xl:col-span-1">
          <div className="space-y-3">
            <h2 className="text-lg font-bold tracking-tight text-ink">가격 흐름</h2>
            <div className="flex gap-1 rounded-lg bg-panel p-1">
              {RANGES.map((item) => (
                <button
                  key={item}
                  type="button"
                  aria-pressed={range === item}
                  className={`h-10 flex-1 rounded-md text-xs font-semibold transition ${
                    range === item ? "bg-surface text-ink shadow-soft" : "text-muted hover:text-body"
                  }`}
                  onClick={() => setRange(item)}
                >
                  {item.toUpperCase()}
                </button>
              ))}
            </div>
            <PriceChart prices={prices.data ?? []} />
          </div>

          <div>
            <h2 className="mb-3 text-lg font-bold tracking-tight text-ink">기준일 변동 내역</h2>
            <ChangeFeed
              changes={holdingChanges.data ?? []}
              isLoading={holdingChanges.isLoading}
              errorMessage={holdingChanges.isError ? "기준일 변동 데이터를 불러오지 못했습니다." : undefined}
              initialVisibleCount={5}
              visibleStep={5}
              dense
            />
          </div>
        </div>
      </div>

      <p className="mt-6 text-xs text-muted">
        본 화면은 발행사 공시 보유 종목을 재가공한 정보이며, 자금흐름은 공시 보유 기준
        추정값입니다. 투자자문이 아닙니다.
      </p>
    </AppShell>
  );
}

function Stat({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="min-w-0 rounded-lg bg-panel px-3 py-2.5">
      <div className="text-[11px] text-faint">{label}</div>
      <div className="mt-1 truncate text-sm font-semibold text-ink">{value}</div>
    </div>
  );
}

function FlowSummary({
  flow,
  snapshotDate,
  isLoading,
  isError
}: {
  flow: EtfFlow | null;
  snapshotDate: string | undefined;
  isLoading: boolean;
  isError: boolean;
}) {
  if (isLoading) {
    return (
      <section className="mt-4 rounded-lg border border-line bg-surface px-4 py-3">
        <FlowSummaryHeader title="자금흐름 추정" subtitle="계산값을 불러오는 중입니다." />
      </section>
    );
  }

  if (isError) {
    return (
      <section className="mt-4 rounded-lg border border-line bg-surface px-4 py-3">
        <FlowSummaryHeader title="자금흐름 추정" subtitle="자금흐름 데이터를 불러오지 못했습니다." />
      </section>
    );
  }

  if (!flow) {
    return (
      <section className="mt-4 rounded-lg border border-line bg-surface px-4 py-3">
        <FlowSummaryHeader
          title="자금흐름 추정 대기"
          subtitle={`${snapshotDate ?? "최신 기준"} · 연속 2개 이상 스냅샷부터 산출됩니다.`}
        />
      </section>
    );
  }

  const netFlowTone = flow.net_flow > 0 ? "text-gain" : flow.net_flow < 0 ? "text-fall" : "text-muted";
  const netFlowLabel = flow.net_flow > 0 ? "순유입" : flow.net_flow < 0 ? "순유출" : "중립";

  return (
    <section className="mt-4 rounded-lg border border-line bg-surface px-4 py-3">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <FlowSummaryHeader
          title={`자금흐름 추정 · ${netFlowLabel}`}
          subtitle={`${flow.prev_date} → ${flow.as_of_date} · 공시 보유 시장가치 기준`}
        />
        <span className="inline-flex h-6 w-fit items-center rounded-full bg-panel px-2.5 text-xs font-medium text-muted ring-1 ring-line">
          추정값
        </span>
      </div>
      <div className="mt-3 grid gap-3 border-t border-hair pt-3 sm:grid-cols-4">
        <FlowMetric label="순자금" value={formatSignedMoney(flow.net_flow)} className={netFlowTone} />
        <FlowMetric label="자금률" value={formatSignedRate(flow.flow_rate)} />
        <FlowMetric label="회전율" value={formatRatioPercent(flow.turnover)} />
        <FlowMetric label="능동성 R²" value={flow.creation_r2 === null ? "-" : flow.creation_r2.toFixed(2)} />
      </div>
      <p className="mt-3 text-xs leading-relaxed text-muted">
        creation/redemption 정밀 데이터가 아니라 보유종목 shares·market value로 추정한 값입니다.
        종목별 태그는 자금흐름분을 뺀 shares 잔차를 NAV bp와 포지션 비중으로 나눈 강도입니다.
      </p>
    </section>
  );
}

function FlowSummaryHeader({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <div>
      <h2 className="text-sm font-bold tracking-tight text-ink">{title}</h2>
      <p className="mt-1 text-xs leading-relaxed text-muted">{subtitle}</p>
    </div>
  );
}

function FlowMetric({
  label,
  value,
  className = "text-ink"
}: {
  label: string;
  value: string;
  className?: string;
}) {
  return (
    <div className="min-w-0">
      <div className="text-[11px] text-faint">{label}</div>
      <div className={`mt-1 truncate text-sm font-semibold tabular-nums ${className}`}>{value}</div>
    </div>
  );
}

function SignalUniverseBadge({
  inUniverse,
  reason
}: {
  inUniverse: boolean;
  reason: string | null;
}) {
  if (inUniverse) {
    return (
      <span className="inline-flex h-6 items-center gap-1.5 rounded-full bg-lime px-2.5 text-xs font-medium leading-none text-gain ring-1 ring-gain/15">
        <span className="h-1.5 w-1.5 rounded-full bg-gain" aria-hidden="true" />
        시그널 분석 대상
      </span>
    );
  }
  return (
    <span
      className="inline-flex h-6 items-center gap-1.5 rounded-full bg-panel px-2.5 text-xs font-medium leading-none text-muted ring-1 ring-line"
      title={reason ?? undefined}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-muted/50" aria-hidden="true" />
      분석 제외{reason ? ` · ${reason}` : ""}
    </span>
  );
}

function formatPercent(value: number | null) {
  return value === null ? "-" : `${value.toFixed(2)}%`;
}

function formatAum(value: number | null) {
  if (value === null) {
    return "-";
  }
  if (Math.abs(value) >= 1_000_000_000) {
    return `$${(value / 1_000_000_000).toFixed(2)}B`;
  }
  if (Math.abs(value) >= 1_000_000) {
    return `$${(value / 1_000_000).toFixed(0)}M`;
  }
  return `$${value.toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
}

function formatSignedMoney(value: number) {
  const sign = value > 0 ? "+" : value < 0 ? "-" : "";
  const abs = Math.abs(value);
  if (abs >= 1_000_000_000) {
    return `${sign}$${(abs / 1_000_000_000).toFixed(2)}B`;
  }
  if (abs >= 1_000_000) {
    return `${sign}$${(abs / 1_000_000).toFixed(1)}M`;
  }
  return `${sign}$${abs.toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
}

function formatSignedRate(value: number) {
  const percent = value * 100;
  const sign = percent > 0 ? "+" : "";
  return `${sign}${percent.toFixed(2)}%`;
}

function formatRatioPercent(value: number) {
  return `${(value * 100).toFixed(2)}%`;
}

function nameKey(name: string) {
  return `NAME:${name.toUpperCase().replace(/[^A-Z0-9]/g, "")}`;
}
