"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchCompare } from "@/lib/api";

export function useCompare(tickers: string[], range: string) {
  return useQuery({
    queryKey: ["compare", tickers, range],
    queryFn: () => fetchCompare(tickers, range),
    enabled: tickers.length >= 2
  });
}

