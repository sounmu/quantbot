"use client";

import Link from "next/link";
import { ChevronLeft, ChevronRight, GitCompare } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { EtfTable } from "@/components/EtfTable";
import { FilterBar } from "@/components/FilterBar";
import { useEtfs, useIssuers, useThemes } from "@/hooks/useEtfs";
import { useWatchlist } from "@/hooks/useWatchlist";
import type { EtfQuery } from "@/lib/types";
import { useState } from "react";

const PAGE_SIZE = 20;

export default function EtfsPage() {
  const [query, setQuery] = useState<EtfQuery>({
    sort: "name",
    order: "asc",
    page: 1,
    page_size: PAGE_SIZE
  });
  const etfs = useEtfs(query);
  const issuers = useIssuers();
  const themes = useThemes();
  const watchlist = useWatchlist();

  const page = query.page ?? 1;
  const total = etfs.data?.total ?? 0;
  const maxPage = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <AppShell>
      <div className="mb-5 flex items-end justify-between gap-3">
        <div className="min-w-0">
          <h1 className="text-2xl font-bold leading-tight tracking-tight text-ink">해외 액티브 ETF</h1>
          <p className="mt-1 text-sm text-muted">공식 보유 종목 공시 추적 목록</p>
        </div>
        <Link
          className="inline-flex min-h-11 shrink-0 items-center justify-center gap-2 rounded-lg bg-brand px-3.5 text-sm font-semibold text-white transition hover:bg-brand/90"
          href="/compare"
        >
          <GitCompare className="h-4 w-4" aria-hidden="true" />
          비교 {watchlist.tickers.length > 0 ? <span className="tabular-nums">{watchlist.tickers.length}</span> : ""}
        </Link>
      </div>

      <div className="space-y-4">
        <FilterBar
          query={query}
          issuers={issuers.data ?? []}
          themes={themes.data ?? []}
          onChange={setQuery}
        />
        <EtfTable
          items={etfs.data?.items ?? []}
          isLoading={etfs.isLoading}
          errorMessage={etfs.isError ? "ETF 목록을 불러오지 못했습니다. API 서버 상태를 확인하세요." : undefined}
          watchlist={watchlist}
        />

        <div className="flex items-center justify-between text-sm text-muted">
          <span className="tabular-nums">
            총 {total.toLocaleString()}개 중 {page} / {maxPage}
          </span>
          <div className="flex items-center gap-2">
            <button
              className="inline-flex h-11 w-11 items-center justify-center rounded-lg border border-line bg-surface text-body transition hover:border-line-strong disabled:opacity-40"
              disabled={page <= 1}
              onClick={() => setQuery((current) => ({ ...current, page: page - 1 }))}
              title="이전"
            >
              <ChevronLeft className="h-4 w-4" aria-hidden="true" />
            </button>
            <button
              className="inline-flex h-11 w-11 items-center justify-center rounded-lg border border-line bg-surface text-body transition hover:border-line-strong disabled:opacity-40"
              disabled={page >= maxPage}
              onClick={() => setQuery((current) => ({ ...current, page: page + 1 }))}
              title="다음"
            >
              <ChevronRight className="h-4 w-4" aria-hidden="true" />
            </button>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
