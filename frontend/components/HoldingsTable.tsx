"use client";

import { useEffect, useMemo, useState } from "react";
import { Search } from "lucide-react";
import { ChangeBadge, CrossSignalBadge, DeltaValue } from "@/components/TradeVisuals";
import type { ChangeType, Holding } from "@/lib/types";

type Props = {
  holdings: Holding[];
  isLoading?: boolean;
  errorMessage?: string;
  selectedKey?: string | null;
  onSelect?: (holdingKey: string, label: string) => void;
};

type FilterKey = "ALL" | ChangeType;
type SortKey = "weight" | "sharesDelta" | "weightDelta";

// EXIT 포지션은 현재 스냅샷에 존재하지 않으므로(이미 청산) 칩에서 제외한다.
const FILTER_ORDER: ChangeType[] = ["NEW", "INCREASE", "DECREASE", "UNCHANGED"];
const FILTER_LABELS: Record<FilterKey, string> = {
  ALL: "전체",
  NEW: "신규",
  INCREASE: "증가",
  DECREASE: "감소",
  UNCHANGED: "유지",
  EXIT: "청산"
};
const SORT_OPTIONS: { key: SortKey; label: string }[] = [
  { key: "weight", label: "비중순" },
  { key: "sharesDelta", label: "주식수 변화순" },
  { key: "weightDelta", label: "비중 변화순" }
];
const PAGE_SIZE = 15;

export function HoldingsTable({ holdings, isLoading, errorMessage, selectedKey, onSelect }: Props) {
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<FilterKey>("ALL");
  const [sort, setSort] = useState<SortKey>("weight");
  const [visible, setVisible] = useState(PAGE_SIZE);

  const counts = useMemo(() => {
    const map: Partial<Record<ChangeType, number>> = {};
    for (const holding of holdings) {
      if (holding.change_type) {
        map[holding.change_type] = (map[holding.change_type] ?? 0) + 1;
      }
    }
    return map;
  }, [holdings]);

  const availableFilters = useMemo<FilterKey[]>(
    () => ["ALL", ...FILTER_ORDER.filter((type) => counts[type])],
    [counts]
  );

  const filtered = useMemo(() => {
    const needle = query.trim().toUpperCase();
    let rows = holdings;
    if (filter !== "ALL") {
      rows = rows.filter((holding) => holding.change_type === filter);
    }
    if (needle) {
      rows = rows.filter(
        (holding) =>
          (holding.holding_ticker ?? "").toUpperCase().includes(needle) ||
          holding.holding_name.toUpperCase().includes(needle)
      );
    }
    const sorted = [...rows];
    sorted.sort((a, b) => {
      if (sort === "sharesDelta") return magnitude(b.shares_delta) - magnitude(a.shares_delta);
      if (sort === "weightDelta") return magnitude(b.weight_delta) - magnitude(a.weight_delta);
      return b.weight - a.weight;
    });
    return sorted;
  }, [holdings, filter, query, sort]);

  // 필터/검색/정렬/스냅샷이 바뀌면 표시 개수를 처음으로 되돌린다.
  useEffect(() => {
    setVisible(PAGE_SIZE);
  }, [filter, query, sort, holdings]);

  // 스냅샷이 바뀌어 현재 필터에 해당하는 종목이 사라지면 전체로 복귀.
  useEffect(() => {
    if (filter !== "ALL" && !counts[filter]) {
      setFilter("ALL");
    }
  }, [counts, filter]);

  let body: React.ReactNode;
  if (errorMessage) {
    body = <StatusCard tone="error">{errorMessage}</StatusCard>;
  } else if (isLoading) {
    body = <StatusCard>불러오는 중</StatusCard>;
  } else if (holdings.length === 0) {
    body = <StatusCard>보유종목 데이터 없음</StatusCard>;
  } else {
    const shown = filtered.slice(0, visible);
    const remaining = filtered.length - shown.length;

    body = (
      <>
        <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-muted">
          <span className="font-semibold tabular-nums text-ink">총 {holdings.length}종목</span>
          {FILTER_ORDER.filter((type) => counts[type]).map((type) => (
            <span key={type}>
              · {FILTER_LABELS[type]} {counts[type]}
            </span>
          ))}
        </div>

        <div className="relative">
          <Search
            className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted"
            aria-hidden="true"
          />
          <input
            className="h-11 w-full rounded-lg border border-line bg-surface pl-9 pr-3 text-sm text-ink placeholder:text-faint focus:border-brand/50"
            placeholder="종목 검색 (티커·이름)"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            aria-label="보유 종목 검색"
            inputMode="search"
            type="search"
          />
        </div>

        <div className="flex items-center gap-2">
          <div className="-mx-1 flex flex-1 gap-1.5 overflow-x-auto px-1 pb-0.5 [-ms-overflow-style:none] [scrollbar-width:none]">
            {availableFilters.map((key) => {
              const active = filter === key;
              const count = key === "ALL" ? holdings.length : counts[key as ChangeType] ?? 0;
              return (
                <button
                  key={key}
                  type="button"
                  aria-pressed={active}
                  onClick={() => setFilter(key)}
                  className={`inline-flex h-8 shrink-0 items-center gap-1 whitespace-nowrap rounded-full px-3 text-xs font-medium ring-1 transition ${
                    active ? "bg-brand text-white ring-brand" : "bg-surface text-muted ring-line hover:text-ink"
                  }`}
                >
                  {FILTER_LABELS[key]}
                  <span className={`tabular-nums ${active ? "text-white/75" : "text-faint"}`}>{count}</span>
                </button>
              );
            })}
          </div>
          <select
            className="h-8 shrink-0 rounded-full border border-line bg-surface px-2 text-xs font-medium text-body"
            value={sort}
            onChange={(event) => setSort(event.target.value as SortKey)}
            aria-label="정렬 기준"
          >
            {SORT_OPTIONS.map((option) => (
              <option key={option.key} value={option.key}>
                {option.label}
              </option>
            ))}
          </select>
        </div>

        {shown.length === 0 ? (
          <StatusCard>조건에 맞는 종목이 없습니다</StatusCard>
        ) : (
          <>
            {/* 모바일: 카드 리스트 */}
            <div className="space-y-3 lg:hidden" role="list">
              {shown.map((holding) => {
                const key = positionKey(holding);
                const label = holding.holding_ticker ?? holding.holding_name;
                const isSelected = selectedKey === key;
                return (
                  <div
                    key={`${holding.as_of_date}-${holding.holding_key}-${holding.holding_name}`}
                    role="listitem"
                  >
                    <button
                      className={`w-full rounded-lg border bg-surface p-4 text-left transition ${
                        isSelected
                          ? "border-brand ring-2 ring-brand/15"
                          : "border-line hover:border-line-strong"
                      }`}
                      type="button"
                      aria-label={`${label} 포지션 선택`}
                      aria-pressed={isSelected}
                      onClick={() => onSelect?.(key, label)}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="text-lg font-bold leading-none tracking-tight text-ink">
                              {holding.holding_ticker ?? "미상"}
                            </span>
                            <ChangeBadge type={holding.change_type} compact />
                            <CrossSignalBadge
                              buying={holding.signal_n_buying}
                              selling={holding.signal_n_selling}
                            />
                          </div>
                          <p className="mt-2 break-words text-sm leading-snug text-muted">
                            {holding.holding_name}
                          </p>
                        </div>
                        <div className="shrink-0 text-right">
                          <div className="text-[11px] text-faint">비중</div>
                          <div className="mt-1 text-sm font-semibold tabular-nums text-ink">
                            {holding.weight.toFixed(2)}%
                          </div>
                        </div>
                      </div>

                      <div className="mt-4 grid grid-cols-2 gap-2 border-t border-hair pt-3 text-xs">
                        <Metric label="주식수" value={formatNumber(holding.shares)} />
                        <Metric
                          label="주식수 변화"
                          value={<DeltaValue value={holding.shares_delta} suffix="" />}
                        />
                        <Metric
                          label="비중 변화"
                          value={<DeltaValue value={holding.weight_delta} suffix="%" />}
                        />
                        <Metric label="시장가치" value={formatMoney(holding.market_value)} />
                      </div>
                    </button>
                  </div>
                );
              })}
            </div>

            {/* 데스크탑: 테이블 */}
            <div className="hidden overflow-hidden rounded-lg border border-line bg-surface lg:block">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-line text-left text-xs font-semibold text-faint">
                    <th className="px-3 py-2.5 pl-4">종목</th>
                    <th className="px-3 py-2.5">이름</th>
                    <th className="px-3 py-2.5">변동</th>
                    <th className="px-3 py-2.5">동반 매매</th>
                    <th className="px-3 py-2.5 text-right">비중</th>
                    <th className="px-3 py-2.5 text-right">주식수</th>
                    <th className="px-3 py-2.5 text-right">주식수 변화</th>
                    <th className="px-3 py-2.5 text-right">비중 변화</th>
                    <th className="px-3 py-2.5 pr-4 text-right">시장가치</th>
                  </tr>
                </thead>
                <tbody>
                  {shown.map((holding) => {
                    const key = positionKey(holding);
                    const label = holding.holding_ticker ?? holding.holding_name;
                    const isSelected = selectedKey === key;
                    return (
                      <tr
                        key={`${holding.as_of_date}-${holding.holding_key}-${holding.holding_name}`}
                        role="button"
                        tabIndex={0}
                        aria-pressed={isSelected}
                        aria-label={`${label} 포지션 선택`}
                        onClick={() => onSelect?.(key, label)}
                        onKeyDown={(event) => {
                          if (event.key === "Enter" || event.key === " ") {
                            event.preventDefault();
                            onSelect?.(key, label);
                          }
                        }}
                        className={`cursor-pointer border-b border-hair last:border-0 transition ${
                          isSelected ? "bg-brand-soft" : "hover:bg-panel"
                        }`}
                      >
                        <td className="py-3 pl-4 font-bold tracking-tight text-ink">
                          {holding.holding_ticker ?? "미상"}
                        </td>
                        <td className="max-w-[260px] truncate py-3 pr-3 text-muted" title={holding.holding_name}>
                          {holding.holding_name}
                        </td>
                        <td className="py-3 pr-3">
                          <ChangeBadge type={holding.change_type} compact />
                        </td>
                        <td className="py-3 pr-3">
                          <CrossSignalBadge
                            buying={holding.signal_n_buying}
                            selling={holding.signal_n_selling}
                          />
                        </td>
                        <td className="py-3 pr-3 text-right tabular-nums text-ink">{holding.weight.toFixed(2)}%</td>
                        <td className="py-3 pr-3 text-right tabular-nums text-body">{formatNumber(holding.shares)}</td>
                        <td className="py-3 pr-3 text-right tabular-nums">
                          <DeltaValue value={holding.shares_delta} suffix="" />
                        </td>
                        <td className="py-3 pr-3 text-right tabular-nums">
                          <DeltaValue value={holding.weight_delta} suffix="%" />
                        </td>
                        <td className="py-3 pr-4 text-right tabular-nums text-body">{formatMoney(holding.market_value)}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </>
        )}

        {remaining > 0 ? (
          <button
            type="button"
            onClick={() => setVisible((value) => value + PAGE_SIZE)}
            className="h-11 w-full rounded-lg border border-line bg-surface text-sm font-semibold text-body transition hover:border-brand/40 hover:text-brand"
          >
            더 보기 <span className="tabular-nums text-faint">· 남은 {remaining}</span>
          </button>
        ) : null}
        {shown.length > 0 ? (
          <p className="text-center text-[11px] tabular-nums text-faint">
            {shown.length} / {filtered.length}종목 표시
          </p>
        ) : null}
      </>
    );
  }

  return (
    <section className="space-y-3" aria-label="보유 종목">
      {body}
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

// 정렬용 크기: null은 -1로 떨어뜨려 항상 맨 뒤로 보낸다.
function magnitude(value: number | null) {
  return value === null ? -1 : Math.abs(value);
}

function formatNumber(value: number | null) {
  if (value === null) {
    return "-";
  }
  return value.toLocaleString(undefined, {
    maximumFractionDigits: Number.isInteger(value) ? 0 : 4
  });
}

function formatMoney(value: number | null) {
  if (value === null) {
    return "-";
  }
  if (Math.abs(value) >= 1_000_000_000) {
    return `$${(value / 1_000_000_000).toFixed(2)}B`;
  }
  if (Math.abs(value) >= 1_000_000) {
    return `$${(value / 1_000_000).toFixed(1)}M`;
  }
  return `$${value.toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
}

function positionKey(holding: Holding) {
  // The backend supplies the canonical holding_key (ID:/NAME:/ticker); use it verbatim so
  // positions with non-unique tickers (e.g. international cross-listings) stay distinct.
  if (holding.holding_key) {
    return holding.holding_key;
  }
  if (holding.holding_ticker) {
    return holding.holding_ticker;
  }
  return `NAME:${holding.holding_name.toUpperCase().replace(/[^A-Z0-9]/g, "")}`;
}
