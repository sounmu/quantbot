"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchAnalysisPerformance, fetchSecurityAnalysis } from "@/lib/api";
import type { HorizonDays, PerformanceBucket } from "@/lib/types";

export function useAnalysisPerformance(horizon: HorizonDays, bucket?: PerformanceBucket) {
  return useQuery({
    queryKey: ["analysis-performance", horizon, bucket],
    queryFn: () => fetchAnalysisPerformance(horizon, bucket)
  });
}

export function useSecurityAnalysis(securityKey: string | null) {
  return useQuery({
    queryKey: ["security-analysis", securityKey],
    queryFn: () => fetchSecurityAnalysis(securityKey ?? ""),
    enabled: Boolean(securityKey)
  });
}
