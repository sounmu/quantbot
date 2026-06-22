"use client";

import { Search } from "lucide-react";
import type { EtfQuery } from "@/lib/types";

type Props = {
  query: EtfQuery;
  issuers: string[];
  themes: string[];
  onChange: (query: EtfQuery) => void;
};

export function FilterBar({ query, issuers, themes, onChange }: Props) {
  return (
    <div className="grid gap-3 rounded-lg border border-line bg-white p-3 shadow-soft md:grid-cols-[minmax(220px,1fr)_180px_180px_180px_120px]">
      <label className="relative block">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
        <input
          className="h-10 w-full rounded-md border border-line bg-white pl-9 pr-3 text-sm text-ink"
          value={query.q ?? ""}
          onChange={(event) => onChange({ ...query, q: event.target.value, page: 1 })}
          placeholder="티커 또는 이름"
        />
      </label>
      <select
        className="h-10 rounded-md border border-line bg-white px-3 text-sm text-ink"
        value={query.issuer ?? ""}
        onChange={(event) => onChange({ ...query, issuer: event.target.value, page: 1 })}
      >
        <option value="">운용사 전체</option>
        {issuers.map((issuer) => (
          <option key={issuer} value={issuer}>
            {issuer}
          </option>
        ))}
      </select>
      <select
        className="h-10 rounded-md border border-line bg-white px-3 text-sm text-ink"
        value={query.theme ?? ""}
        onChange={(event) => onChange({ ...query, theme: event.target.value, page: 1 })}
      >
        <option value="">테마 전체</option>
        {themes.map((theme) => (
          <option key={theme} value={theme}>
            {theme}
          </option>
        ))}
      </select>
      <select
        className="h-10 rounded-md border border-line bg-white px-3 text-sm text-ink"
        value={query.sort ?? "name"}
        onChange={(event) =>
          onChange({ ...query, sort: event.target.value as EtfQuery["sort"], page: 1 })
        }
      >
        <option value="name">이름순</option>
        <option value="expense_ratio">보수율</option>
        <option value="return_ytd">YTD 수익률</option>
        <option value="return_1y">1Y 수익률</option>
      </select>
      <select
        className="h-10 rounded-md border border-line bg-white px-3 text-sm text-ink"
        value={query.order ?? "asc"}
        onChange={(event) =>
          onChange({ ...query, order: event.target.value as EtfQuery["order"], page: 1 })
        }
      >
        <option value="asc">오름차순</option>
        <option value="desc">내림차순</option>
      </select>
    </div>
  );
}

