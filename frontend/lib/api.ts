import type {
  CompareResponse,
  EtfDetail,
  EtfListResponse,
  EtfQuery,
  HoldingChange,
  Holding,
  HorizonDays,
  PerformanceBucket,
  PerformanceSummary,
  PositionHistoryPoint,
  PricePoint,
  SecurityAnalysisPoint,
  SignalDaily,
  SignalSecurityHistory
} from "./types";

const API_BASE_URL = (process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000").replace(
  /\/$/,
  ""
);

async function fetchJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`);
  if (!response.ok) {
    throw new Error(`API ${response.status}: ${response.statusText}`);
  }
  return response.json() as Promise<T>;
}

function toSearchParams(params: Record<string, string | number | undefined>) {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== "") {
      search.set(key, String(value));
    }
  });
  const query = search.toString();
  return query ? `?${query}` : "";
}

export function fetchEtfs(query: EtfQuery) {
  return fetchJson<EtfListResponse>(`/api/etfs${toSearchParams(query)}`);
}

export function fetchEtfDetail(ticker: string) {
  return fetchJson<EtfDetail>(`/api/etfs/${ticker}`);
}

export function fetchEtfPrices(ticker: string, range: string) {
  return fetchJson<PricePoint[]>(`/api/etfs/${ticker}/prices${toSearchParams({ range })}`);
}

export function fetchHoldings(ticker: string, date?: string) {
  return fetchJson<Holding[]>(`/api/etfs/${ticker}/holdings${toSearchParams({ date })}`);
}

export function fetchHoldingDates(ticker: string) {
  return fetchJson<string[]>(`/api/etfs/${ticker}/holdings/dates`);
}

export function fetchHoldingChanges(ticker: string, date?: string) {
  return fetchJson<HoldingChange[]>(`/api/etfs/${ticker}/changes${toSearchParams({ date })}`);
}

export function fetchPositionHistory(ticker: string, holding: string) {
  return fetchJson<PositionHistoryPoint[]>(
    `/api/etfs/${ticker}/positions/${encodeURIComponent(holding)}/history`
  );
}

export function fetchRecentChanges(limit = 100) {
  return fetchJson<HoldingChange[]>(`/api/changes/recent${toSearchParams({ limit })}`);
}

export function fetchIssuers() {
  return fetchJson<string[]>("/api/meta/issuers");
}

export function fetchThemes() {
  return fetchJson<string[]>("/api/meta/themes");
}

export function fetchCompare(tickers: string[], range: string) {
  return fetchJson<CompareResponse>(
    `/api/etfs/compare${toSearchParams({ tickers: tickers.join(","), range })}`
  );
}

export function fetchDailySignals(limit = 100, date?: string) {
  return fetchJson<SignalDaily[]>(`/api/signals/daily${toSearchParams({ limit, date })}`);
}

export function fetchSignalSecurityHistory(securityKey: string, limit = 100) {
  return fetchJson<SignalSecurityHistory[]>(
    `/api/signals/security/${encodeURIComponent(securityKey)}${toSearchParams({ limit })}`
  );
}

export function fetchAnalysisPerformance(horizon?: HorizonDays, bucket?: PerformanceBucket) {
  return fetchJson<PerformanceSummary[]>(
    `/api/analysis/performance${toSearchParams({ horizon, bucket })}`
  );
}

export function fetchSecurityAnalysis(securityKey: string) {
  return fetchJson<SecurityAnalysisPoint[]>(
    `/api/analysis/security/${encodeURIComponent(securityKey)}`
  );
}
