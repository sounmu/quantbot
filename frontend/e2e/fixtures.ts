import type { Page } from "@playwright/test";

const SEEDED = {
  etfs: {
    items: [
      {
        ticker: "DYNF",
        name: "iShares U.S. Equity Factor Rotation Active ETF",
        issuer: "BlackRock",
        theme: "Multi-Factor",
        expense_ratio: 0.25,
        discloses_daily: true,
        return_1m: 2.1,
        return_3m: 5.8,
        return_ytd: 12.4,
        return_1y: 18.9,
      },
      {
        ticker: "ARKK",
        name: "ARK Innovation ETF",
        issuer: "ARK",
        theme: "Innovation",
        expense_ratio: 0.75,
        discloses_daily: true,
        return_1m: -1.2,
        return_3m: 3.4,
        return_ytd: -5.6,
        return_1y: -12.3,
      },
      {
        ticker: "CGGR",
        name: "Capital Group Growth ETF",
        issuer: "Capital Group",
        theme: "Growth",
        expense_ratio: 0.39,
        discloses_daily: true,
        return_1m: 3.2,
        return_3m: 8.1,
        return_ytd: 20.5,
        return_1y: 28.7,
      },
      {
        ticker: "AVUV",
        name: "Avantis U.S. Small Cap Value ETF",
        issuer: "Avantis",
        theme: "Small Cap Value",
        expense_ratio: 0.25,
        discloses_daily: true,
        return_1m: 0.5,
        return_3m: 2.1,
        return_ytd: 4.3,
        return_1y: 8.2,
      },
    ],
    total: 4,
    page: 1,
    page_size: 20,
  },

  issuers: ["ARK", "Avantis", "BlackRock", "Capital Group"],
  themes: ["Growth", "Innovation", "Multi-Factor", "Small Cap Value"],

  etfDetail: {
    ticker: "DYNF",
    name: "iShares U.S. Equity Factor Rotation Active ETF",
    issuer: "BlackRock",
    theme: "Multi-Factor",
    expense_ratio: 0.25,
    discloses_daily: true,
    return_1m: 2.1,
    return_3m: 5.8,
    return_ytd: 12.4,
    return_1y: 18.9,
    inception_date: "2023-04-01",
    currency: "USD",
    description: "A factor rotation ETF that dynamically allocates across U.S. equities.",
    as_of: "2026-06-24",
    aum: 37_500_000_000,
  },

  holdings: [
    { as_of_date: "2026-06-24", holding_key: "ID:NVDA", holding_ticker: "NVDA", security_id: "67066G104", holding_name: "NVIDIA CORP", weight: 8.54, shares: 15211230, market_value: 3204854048.70, change_type: "INCREASE", shares_delta: 211230, shares_delta_pct: 1.41, weight_delta: 0.24, signal_n_buying: 3, signal_n_selling: 0, signal_conviction: 3, flow_adjusted: "BUY", active_direction: "BUY", active_intensity: "MEDIUM", active_confidence: "HIGH", active_residual: 120000, passive_shares: 91230, residual_nav_bp: 8.5, residual_position_pct: 0.0079 },
    { as_of_date: "2026-06-24", holding_key: "ID:AAPL", holding_ticker: "AAPL", security_id: "037833100", holding_name: "APPLE INC", weight: 7.53, shares: 9482129, market_value: 2825769263.29, change_type: "UNCHANGED", shares_delta: 0, shares_delta_pct: 0, weight_delta: 0, signal_n_buying: 0, signal_n_selling: 0, signal_conviction: 0, flow_adjusted: "HOLD", active_direction: "NEUTRAL", active_intensity: "NONE", active_confidence: "HIGH", active_residual: 0.4, passive_shares: -0.4, residual_nav_bp: 0.0, residual_position_pct: 0.0 },
    { as_of_date: "2026-06-24", holding_key: "ID:MSFT", holding_ticker: "MSFT", security_id: "594918104", holding_name: "MICROSOFT CORP", weight: 5.60, shares: 5678901, market_value: 2100000000.00, change_type: "DECREASE", shares_delta: -100000, shares_delta_pct: -1.73, weight_delta: -0.15, signal_n_buying: 0, signal_n_selling: 1, signal_conviction: -1, flow_adjusted: "SELL", active_direction: "SELL", active_intensity: "MEDIUM", active_confidence: "HIGH", active_residual: -85000, passive_shares: -15000, residual_nav_bp: 6.8, residual_position_pct: 0.015 },
  ],

  flow: [
    {
      ticker: "DYNF",
      as_of_date: "2026-06-24",
      prev_date: "2026-06-23",
      net_flow: 125000000,
      flow_rate: 0.0034,
      active_buy: 82000000,
      active_sell: 39000000,
      turnover: 0.018,
      creation_r2: 0.64,
    },
  ],

  holdingDates: ["2026-06-24", "2026-06-23", "2026-06-20"],

  prices: [
    { date: "2026-06-01", open: 45.0, high: 46.0, low: 44.5, close: 45.8, nav: 45.75, volume: 1000000 },
    { date: "2026-06-20", open: 46.5, high: 47.5, low: 46.0, close: 47.2, nav: 47.15, volume: 1200000 },
  ],

  changes: [
    {
      ticker: "DYNF", as_of_date: "2026-06-24", prev_date: "2026-06-23",
      holding_ticker: "NVDA", holding_name: "NVIDIA CORP", change_type: "INCREASE",
      shares_before: 15000000, shares_after: 15211230, shares_delta: 211230,
      shares_delta_pct: 1.41, weight_before: 8.3, weight_after: 8.54, weight_delta: 0.24,
    },
    {
      ticker: "ARKK", as_of_date: "2026-06-24", prev_date: "2026-06-23",
      holding_ticker: "TSLA", holding_name: "TESLA INC", change_type: "EXIT",
      shares_before: 1632909, shares_after: 0, shares_delta: -1632909,
      shares_delta_pct: -100, weight_before: 9.68, weight_after: 0, weight_delta: -9.68,
    },
    {
      ticker: "CGGR", as_of_date: "2026-06-24", prev_date: "2026-06-23",
      holding_ticker: "META", holding_name: "META PLATFORMS INC", change_type: "NEW",
      shares_before: 0, shares_after: 2814677, shares_delta: 2814677,
      shares_delta_pct: null, weight_before: 0, weight_after: 6.57, weight_delta: 6.57,
    },
    {
      ticker: "DYNF", as_of_date: "2026-06-24", prev_date: "2026-06-23",
      holding_ticker: "AMZN", holding_name: "AMAZON COM INC", change_type: "INCREASE",
      shares_before: 5000000, shares_after: 5100000, shares_delta: 100000,
      shares_delta_pct: 2, weight_before: 3.1, weight_after: 3.22, weight_delta: 0.12,
    },
    {
      ticker: "DYNF", as_of_date: "2026-06-24", prev_date: "2026-06-23",
      holding_ticker: "GOOGL", holding_name: "ALPHABET INC", change_type: "DECREASE",
      shares_before: 4200000, shares_after: 4100000, shares_delta: -100000,
      shares_delta_pct: -2.38, weight_before: 2.9, weight_after: 2.81, weight_delta: -0.09,
    },
    {
      ticker: "DYNF", as_of_date: "2026-06-24", prev_date: "2026-06-23",
      holding_ticker: "JPM", holding_name: "JPMORGAN CHASE & CO", change_type: "NEW",
      shares_before: 0, shares_after: 900000, shares_delta: 900000,
      shares_delta_pct: null, weight_before: 0, weight_after: 1.14, weight_delta: 1.14,
    },
  ],

  recentChanges: [
    {
      ticker: "DYNF", as_of_date: "2026-06-24", prev_date: "2026-06-23",
      holding_ticker: "NVDA", holding_name: "NVIDIA CORP", change_type: "INCREASE",
      shares_before: 15000000, shares_after: 15211230, shares_delta: 211230,
      shares_delta_pct: 1.41, weight_before: 8.3, weight_after: 8.54, weight_delta: 0.24,
    },
    {
      ticker: "ARKK", as_of_date: "2026-06-24", prev_date: "2026-06-23",
      holding_ticker: "TSLA", holding_name: "TESLA INC", change_type: "EXIT",
      shares_before: 1632909, shares_after: 0, shares_delta: -1632909,
      shares_delta_pct: -100, weight_before: 9.68, weight_after: 0, weight_delta: -9.68,
    },
  ],

  dailySignals: [
    {
      security_key: "ID:NVDA",
      as_of_date: "2026-06-24",
      security_ticker: "NVDA",
      security_name: "NVIDIA CORP",
      n_buying: 3,
      n_selling: 0,
      net_shares_flow: 421230,
      net_dollar_flow: 52000000,
      conviction_score: 3,
    },
    {
      security_key: "ID:META",
      as_of_date: "2026-06-24",
      security_ticker: "META",
      security_name: "META PLATFORMS INC",
      n_buying: 2,
      n_selling: 0,
      net_shares_flow: 2814677,
      net_dollar_flow: 180000000,
      conviction_score: 2,
    },
  ],

  signalHistory: [
    {
      security_key: "ID:NVDA",
      as_of_date: "2026-06-24",
      security_ticker: "NVDA",
      security_name: "NVIDIA CORP",
      n_buying: 3,
      n_selling: 0,
      net_shares_flow: 421230,
      net_dollar_flow: 52000000,
      conviction_score: 3,
      participants: [
        {
          etf_ticker: "DYNF",
          etf_name: "iShares U.S. Equity Factor Rotation Active ETF",
          issuer: "BlackRock",
          direction: "BUY",
          change_type: "INCREASE",
          shares_delta: 211230,
          shares_delta_pct: 1.41,
          weight_delta: 0.24,
        },
        {
          etf_ticker: "CGGR",
          etf_name: "Capital Group Growth ETF",
          issuer: "Capital Group",
          direction: "BUY",
          change_type: "INCREASE",
          shares_delta: 120000,
          shares_delta_pct: 2.1,
          weight_delta: 0.32,
        },
      ],
    },
  ],

  performance: [
    {
      bucket: "all",
      horizon_days: 20,
      sample_size: 42,
      hit_rate: 0.57,
      average_excess_return: 0.018,
      median_excess_return: 0.012,
      information_coefficient: 0.21,
    },
    {
      bucket: "conviction_1",
      horizon_days: 20,
      sample_size: 30,
      hit_rate: 0.5,
      average_excess_return: 0.004,
      median_excess_return: 0.002,
      information_coefficient: 0.05,
    },
    {
      bucket: "conviction_2_plus",
      horizon_days: 20,
      sample_size: 12,
      hit_rate: 0.67,
      average_excess_return: 0.031,
      median_excess_return: 0.024,
      information_coefficient: 0.33,
    },
    {
      bucket: "conviction_3_plus",
      horizon_days: 20,
      sample_size: 4,
      hit_rate: 0.75,
      average_excess_return: 0.044,
      median_excess_return: 0.039,
      information_coefficient: null,
    },
  ],

  securityAnalysis: [
    {
      as_of_date: "2026-06-03",
      horizon_days: 20,
      start_date: "2026-06-04",
      end_date: "2026-06-30",
      stock_return: 0.072,
      benchmark_return: 0.031,
      excess_return: 0.041,
      signal_score: 2,
    },
    {
      as_of_date: "2026-06-24",
      horizon_days: 20,
      start_date: "2026-06-25",
      end_date: "2026-07-23",
      stock_return: 0.096,
      benchmark_return: 0.037,
      excess_return: 0.059,
      signal_score: 3,
    },
  ],

  compare: {
    items: [
      { ticker: "DYNF", name: "iShares Factor ETF", issuer: "BlackRock", theme: "Multi-Factor", expense_ratio: 0.25, discloses_daily: true, return_1m: 2.1, return_3m: 5.8, return_ytd: 12.4, return_1y: 18.9, as_of: "2026-06-24", aum: 37500000000 },
      { ticker: "ARKK", name: "ARK Innovation ETF", issuer: "ARK", theme: "Innovation", expense_ratio: 0.75, discloses_daily: true, return_1m: -1.2, return_3m: 3.4, return_ytd: -5.6, return_1y: -12.3, as_of: "2026-06-24", aum: 6750000000 },
    ],
    series: {
      DYNF: [{ date: "2026-06-01", close: 45.8, normalized_return: 1.0 }, { date: "2026-06-20", close: 47.2, normalized_return: 1.0306 }],
      ARKK: [{ date: "2026-06-01", close: 50.0, normalized_return: 1.0 }, { date: "2026-06-20", close: 48.5, normalized_return: 0.97 }],
    },
  },
};

export async function mockApi(page: Page) {
  await page.route("**/api/etfs?*", (route) => {
    route.fulfill({ status: 200, json: SEEDED.etfs, headers: { "Access-Control-Allow-Origin": "*" } });
  });
  await page.route("**/api/meta/issuers", (route) => {
    route.fulfill({ status: 200, json: SEEDED.issuers, headers: { "Access-Control-Allow-Origin": "*" } });
  });
  await page.route("**/api/meta/themes", (route) => {
    route.fulfill({ status: 200, json: SEEDED.themes, headers: { "Access-Control-Allow-Origin": "*" } });
  });
  await page.route("**/api/etfs/*/prices*", (route) => {
    route.fulfill({ status: 200, json: SEEDED.prices, headers: { "Access-Control-Allow-Origin": "*" } });
  });
  await page.route("**/api/etfs/*/flow*", (route) => {
    route.fulfill({ status: 200, json: SEEDED.flow, headers: { "Access-Control-Allow-Origin": "*" } });
  });
  await page.route("**/api/etfs/*/holdings**", (route) => {
    route.fulfill({ status: 200, json: SEEDED.holdings, headers: { "Access-Control-Allow-Origin": "*" } });
  });
  await page.route("**/api/etfs/*/holdings/dates", (route) => {
    route.fulfill({ status: 200, json: SEEDED.holdingDates, headers: { "Access-Control-Allow-Origin": "*" } });
  });
  await page.route("**/api/etfs/*/changes*", (route) => {
    route.fulfill({ status: 200, json: SEEDED.changes, headers: { "Access-Control-Allow-Origin": "*" } });
  });
  await page.route("**/api/changes/recent*", (route) => {
    route.fulfill({ status: 200, json: SEEDED.recentChanges, headers: { "Access-Control-Allow-Origin": "*" } });
  });
  await page.route("**/api/signals/daily*", (route) => {
    route.fulfill({ status: 200, json: SEEDED.dailySignals, headers: { "Access-Control-Allow-Origin": "*" } });
  });
  await page.route("**/api/signals/security/**", (route) => {
    route.fulfill({ status: 200, json: SEEDED.signalHistory, headers: { "Access-Control-Allow-Origin": "*" } });
  });
  await page.route("**/api/analysis/performance*", (route) => {
    route.fulfill({ status: 200, json: SEEDED.performance, headers: { "Access-Control-Allow-Origin": "*" } });
  });
  await page.route("**/api/analysis/security/**", (route) => {
    route.fulfill({ status: 200, json: SEEDED.securityAnalysis, headers: { "Access-Control-Allow-Origin": "*" } });
  });
  await page.route("**/api/etfs/compare*", (route) => {
    route.fulfill({ status: 200, json: SEEDED.compare, headers: { "Access-Control-Allow-Origin": "*" } });
  });
  // Catch-all for individual ETF detail
  await page.route("**/api/etfs/DYNF", (route) => {
    route.fulfill({ status: 200, json: SEEDED.etfDetail, headers: { "Access-Control-Allow-Origin": "*" } });
  });
  await page.route("**/api/etfs/ARKK", (route) => {
    const arkkItem = SEEDED.etfs.items.find((e) => e.ticker === "ARKK")!;
    route.fulfill({ status: 200, json: { ...arkkItem, inception_date: "2014-10-31", currency: "USD", description: "ARK Innovation ETF", as_of: "2026-06-24", aum: 6750000000 }, headers: { "Access-Control-Allow-Origin": "*" } });
  });
}

export async function mockApiError(page: Page) {
  await page.route("**/api/**", (route) => {
    route.fulfill({ status: 500, json: { detail: "Internal Server Error" }, headers: { "Access-Control-Allow-Origin": "*" } });
  });
}
