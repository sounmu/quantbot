"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchDailySignals, fetchSignalSecurityHistory } from "@/lib/api";

export function useDailySignals(limit = 100, date?: string) {
  return useQuery({
    queryKey: ["daily-signals", limit, date],
    queryFn: () => fetchDailySignals(limit, date)
  });
}

export function useSignalSecurityHistory(securityKey: string | null, limit = 100) {
  return useQuery({
    queryKey: ["signal-security-history", securityKey, limit],
    queryFn: () => fetchSignalSecurityHistory(securityKey ?? "", limit),
    enabled: Boolean(securityKey)
  });
}
