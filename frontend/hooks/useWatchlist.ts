"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

const STORAGE_KEY = "quantbot.watchlist";

export function useWatchlist() {
  const [tickers, setTickers] = useState<string[]>([]);
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      setIsReady(true);
      return;
    }
    try {
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed)) {
        setTickers(normalizeTickers(parsed.filter((value) => typeof value === "string")));
      }
    } catch {
      setTickers([]);
    } finally {
      setIsReady(true);
    }
  }, []);

  const toggle = useCallback((ticker: string) => {
    const normalized = ticker.toUpperCase();
    setTickers((current) => {
      const next = current.includes(normalized)
        ? current.filter((item) => item !== normalized)
        : [...current, normalized].sort();
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
      return next;
    });
  }, []);

  const has = useCallback((ticker: string) => tickers.includes(ticker.toUpperCase()), [tickers]);

  return useMemo(() => ({ tickers, isReady, toggle, has }), [tickers, isReady, toggle, has]);
}

function normalizeTickers(values: string[]) {
  return Array.from(new Set(values.map((value) => value.trim().toUpperCase()).filter(Boolean))).sort();
}
