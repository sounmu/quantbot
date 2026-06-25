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
        <Link className="inline-flex items-center gap-2 text-sm text-muted hover:text-ink" href="/etfs">
          <ArrowLeft className="h-4 w-4" aria-hidden="true" />
          목록
        </Link>
      </div>

      <div className="mb-5 rounded-lg border border-line bg-white p-5 shadow-soft">
        <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-3xl font-semibold text-ink">{ticker}</h1>
              <button
                className="inline-flex h-9 w-9 items-center justify-center rounded-md text-muted hover:bg-panel hover:text-berry"
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
            <p className="mt-1 max-w-3xl text-sm text-muted">
              {detail.data?.name ?? (detail.isLoading ? "불러오는 중" : "ETF 정보 없음")}
            </p>
          </div>
          <div className="grid grid-cols-2 gap-3 text-sm md:grid-cols-4">
            <Stat label="운용사" value={detail.data?.issuer ?? "-"} />
            <Stat label="테마" value={detail.data?.theme ?? "-"} />
            <Stat label="보수율" value={formatPercent(detail.data?.expense_ratio ?? null)} />
            <Stat label="공시" value={detail.data?.discloses_daily ? "일별" : "미지원"} />
          </div>
        </div>
      </div>

      <div className="mb-3 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="text-lg font-semibold text-ink">보유 종목 스냅샷</h2>
          <p className="mt-1 text-sm text-muted">
            주식수 Δ 기준으로 실제 매매 방향을 판정하고, 비중 Δ는 보조 지표로 표시합니다.
          </p>
        </div>
        <select
          className="h-10 rounded-md border border-line bg-white px-3 text-sm text-ink"
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

      <div className="grid gap-5 2xl:grid-cols-[minmax(0,1fr)_380px]">
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
        <PositionHistoryChart
          points={positionHistory.data ?? []}
          label={selectedPositionLabel}
          isLoading={positionHistory.isLoading}
        />
      </div>

      <div className="mt-6">
        <h2 className="mb-3 text-lg font-semibold text-ink">스냅샷 변동 피드</h2>
        <ChangeFeed
          changes={holdingChanges.data ?? []}
          isLoading={holdingChanges.isLoading}
          errorMessage={holdingChanges.isError ? "스냅샷 변동 데이터를 불러오지 못했습니다." : undefined}
        />
      </div>

      <div className="mb-3 mt-6 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-ink">가격 컨텍스트</h2>
        <div className="flex rounded-md border border-line bg-white p-1">
          {RANGES.map((item) => (
            <button
              key={item}
              className={`h-8 min-w-12 rounded px-3 text-xs font-medium ${
                range === item ? "bg-ink text-white" : "text-muted hover:bg-panel"
              }`}
              onClick={() => setRange(item)}
            >
              {item.toUpperCase()}
            </button>
          ))}
        </div>
      </div>
      <PriceChart prices={prices.data ?? []} />

      <p className="mt-6 text-xs text-muted">
        본 화면은 발행사 공시 holdings를 재가공한 정보이며 투자자문이 아닙니다.
      </p>
    </AppShell>
  );
}

function Stat({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="min-w-28 rounded-md border border-line bg-panel px-3 py-2">
      <div className="text-xs text-muted">{label}</div>
      <div className="mt-1 text-sm font-semibold text-ink">{value}</div>
    </div>
  );
}

function formatPercent(value: number | null) {
  return value === null ? "-" : `${value.toFixed(2)}%`;
}

function nameKey(name: string) {
  return `NAME:${name.toUpperCase().replace(/[^A-Z0-9]/g, "")}`;
}
