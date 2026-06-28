export type EtfListItem = {
  ticker: string;
  name: string;
  issuer: string;
  theme: string | null;
  expense_ratio: number | null;
  exchange: string | null;
  aum: number | null;
  in_signal_universe: boolean;
  signal_universe_reason: string | null;
  discloses_daily: boolean;
  return_1m: number | null;
  return_3m: number | null;
  return_ytd: number | null;
  return_1y: number | null;
};

export type EtfDetail = EtfListItem & {
  inception_date: string | null;
  currency: string;
  description: string | null;
  as_of: string | null;
};

export type EtfListResponse = {
  items: EtfListItem[];
  total: number;
  page: number;
  page_size: number;
};

export type PricePoint = {
  date: string;
  open: number | null;
  high: number | null;
  low: number | null;
  close: number;
  nav: number | null;
  volume: number | null;
};

export type Holding = {
  as_of_date: string;
  holding_key: string;
  holding_ticker: string | null;
  security_id: string | null;
  holding_name: string;
  weight: number;
  shares: number | null;
  market_value: number | null;
  change_type: ChangeType | null;
  shares_delta: number | null;
  shares_delta_pct: number | null;
  weight_delta: number | null;
  // 같은 날 이 종목을 매매한 시그널 유니버스 ETF 수 (교차 시그널)
  signal_n_buying: number | null;
  signal_n_selling: number | null;
  signal_conviction: number | null;
};

export type ChangeType = "NEW" | "EXIT" | "INCREASE" | "DECREASE" | "UNCHANGED";

export type HoldingChange = {
  ticker: string;
  as_of_date: string;
  prev_date: string | null;
  holding_ticker: string | null;
  holding_name: string;
  change_type: ChangeType;
  shares_before: number | null;
  shares_after: number | null;
  shares_delta: number | null;
  shares_delta_pct: number | null;
  weight_before: number | null;
  weight_after: number | null;
  weight_delta: number | null;
};

export type PositionHistoryPoint = {
  as_of_date: string;
  holding_ticker: string | null;
  holding_name: string;
  shares: number | null;
  weight: number;
  market_value: number | null;
};

export type CompareResponse = {
  items: EtfListItem[];
  series: Record<string, Array<{ date: string; close: number; normalized_return: number }>>;
};

export type SignalDirection = "BUY" | "SELL";

export type SignalDaily = {
  security_key: string;
  as_of_date: string;
  security_ticker: string;
  security_name: string;
  n_buying: number;
  n_selling: number;
  net_shares_flow: number | null;
  net_dollar_flow: number | null;
  conviction_score: number;
};

export type SignalParticipant = {
  etf_ticker: string;
  etf_name: string;
  issuer: string;
  direction: SignalDirection;
  change_type: ChangeType;
  shares_delta: number | null;
  shares_delta_pct: number | null;
  weight_delta: number | null;
};

export type SignalSecurityHistory = SignalDaily & {
  participants: SignalParticipant[];
};

export type HorizonDays = 1 | 5 | 20 | 60;

export type PerformanceBucket = "all" | "conviction_1" | "conviction_2_plus" | "conviction_3_plus";

export type PerformanceSummary = {
  bucket: PerformanceBucket;
  horizon_days: HorizonDays;
  sample_size: number;
  hit_rate: number | null;
  average_excess_return: number | null;
  median_excess_return: number | null;
  information_coefficient: number | null;
};

export type SecurityAnalysisPoint = {
  as_of_date: string;
  horizon_days: HorizonDays;
  start_date: string;
  end_date: string;
  stock_return: number;
  benchmark_return: number;
  excess_return: number;
  signal_score: number;
};

export type EtfQuery = {
  q?: string;
  issuer?: string;
  theme?: string;
  sort?: "name" | "expense_ratio" | "return_ytd" | "return_1y";
  order?: "asc" | "desc";
  page?: number;
  page_size?: number;
};
