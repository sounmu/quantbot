"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchEtfs, fetchIssuers, fetchThemes } from "@/lib/api";
import type { EtfQuery } from "@/lib/types";

export function useEtfs(query: EtfQuery) {
  return useQuery({
    queryKey: ["etfs", query],
    queryFn: () => fetchEtfs(query)
  });
}

export function useIssuers() {
  return useQuery({
    queryKey: ["issuers"],
    queryFn: fetchIssuers
  });
}

export function useThemes() {
  return useQuery({
    queryKey: ["themes"],
    queryFn: fetchThemes
  });
}

