"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchRecentChanges } from "@/lib/api";

export function useRecentChanges(limit = 100) {
  return useQuery({
    queryKey: ["recent-changes", limit],
    queryFn: () => fetchRecentChanges(limit)
  });
}
