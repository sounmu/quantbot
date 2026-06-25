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
    { as_of_date: "2026-06-24", holding_key: "ID:NVDA", holding_ticker: "NVDA", security_id: "67066G104", holding_name: "NVIDIA CORP", weight: 8.54, shares: 15211230, market_value: 3204854048.70, change_type: "INCREASE", shares_delta: 211230, shares_delta_pct: 1.41, weight_delta: 0.24 },
    { as_of_date: "2026-06-24", holding_key: "ID:AAPL", holding_ticker: "AAPL", security_id: "037833100", holding_name: "APPLE INC", weight: 7.53, shares: 9482129, market_value: 2825769263.29, change_type: "UNCHANGED", shares_delta: 0, shares_delta_pct: 0, weight_delta: 0 },
    { as_of_date: "2026-06-24", holding_key: "ID:MSFT", holding_ticker: "MSFT", security_id: "594918104", holding_name: "MICROSOFT CORP", weight: 5.60, shares: 5678901, market_value: 2100000000.00, change_type: "DECREASE", shares_delta: -100000, shares_delta_pct: -1.73, weight_delta: -0.15 },
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
  await page.route("**/api/etfs/*/holdings?*", (route) => {
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
