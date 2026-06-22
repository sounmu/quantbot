"use client";

import { useQuery } from "@tanstack/react-query";
import {
  fetchEtfDetail,
  fetchEtfPrices,
  fetchHoldingChanges,
  fetchHoldingDates,
  fetchHoldings,
  fetchPositionHistory
} from "@/lib/api";

export function useEtfDetail(ticker: string) {
  return useQuery({
    queryKey: ["etf", ticker],
    queryFn: () => fetchEtfDetail(ticker),
    enabled: ticker.length > 0
  });
}

export function useEtfPrices(ticker: string, range: string) {
  return useQuery({
    queryKey: ["prices", ticker, range],
    queryFn: () => fetchEtfPrices(ticker, range),
    enabled: ticker.length > 0
  });
}

export function useHoldings(ticker: string, date?: string) {
  return useQuery({
    queryKey: ["holdings", ticker, date],
    queryFn: () => fetchHoldings(ticker, date),
    enabled: ticker.length > 0
  });
}

export function useHoldingDates(ticker: string) {
  return useQuery({
    queryKey: ["holding-dates", ticker],
    queryFn: () => fetchHoldingDates(ticker),
    enabled: ticker.length > 0
  });
}

export function useHoldingChanges(ticker: string, date?: string) {
  return useQuery({
    queryKey: ["holding-changes", ticker, date],
    queryFn: () => fetchHoldingChanges(ticker, date),
    enabled: ticker.length > 0
  });
}

export function usePositionHistory(ticker: string, holding: string | null) {
  return useQuery({
    queryKey: ["position-history", ticker, holding],
    queryFn: () => fetchPositionHistory(ticker, holding ?? ""),
    enabled: ticker.length > 0 && Boolean(holding)
  });
}
