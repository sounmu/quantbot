"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft, Star } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { ChangeFeed } from "@/components/ChangeFeed";
import { HoldingsTable } from "@/components/HoldingsTable";
import { PositionHistoryChart } from "@/components/PositionHistoryChart";
import { PriceChart } from "@/components/PriceChart";
import {
  useEtfDetail,
  useEtfPrices,
  useHoldingChanges,
  useHoldingDates,
  useHoldings,
  usePositionHistory
} from "@/hooks/useEtfDetail";
import { useWatchlist } from "@/hooks/useWatchlist";
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
  const holdingDates = useHoldingDates(ticker);
  const holdings = useHoldings(ticker, snapshotDate);
  const holdingChanges = useHoldingChanges(ticker, snapshotDate);
  const positionHistory = usePositionHistory(ticker, selectedPosition);
  const watchlist = useWatchlist();

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

        <div className="mt-4 grid grid-cols-2 gap-2 text-sm sm:grid-cols-4">
          <Stat label="운용사" value={detail.data?.issuer ?? "-"} />
          <Stat label="테마" value={detail.data?.theme ?? "-"} />
          <Stat label="보수율" value={formatPercent(detail.data?.expense_ratio ?? null)} />
          <Stat label="공시" value={detail.data?.discloses_daily ? "일별" : "미지원"} />
        </div>
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
        본 화면은 발행사 공시 보유 종목을 재가공한 정보이며 투자자문이 아닙니다.
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

function formatPercent(value: number | null) {
  return value === null ? "-" : `${value.toFixed(2)}%`;
}

function nameKey(name: string) {
  return `NAME:${name.toUpperCase().replace(/[^A-Z0-9]/g, "")}`;
}
