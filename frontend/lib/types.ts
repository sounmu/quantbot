export type EtfListItem = {
  ticker: string;
  name: string;
  issuer: string;
  theme: string | null;
  expense_ratio: number | null;
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
  aum: number | null;
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

export type EtfQuery = {
  q?: string;
  issuer?: string;
  theme?: string;
  sort?: "name" | "expense_ratio" | "return_ytd" | "return_1y";
  order?: "asc" | "desc";
  page?: number;
  page_size?: number;
};
