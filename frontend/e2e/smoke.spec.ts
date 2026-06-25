import { test, expect } from "@playwright/test";
import { mockApi, mockApiError } from "./fixtures";

test.describe("ETF list page", () => {
  test("renders ETF table with seeded data", async ({ page }) => {
    await mockApi(page);
    await page.goto("/etfs");

    await expect(page.locator("h1")).toContainText("해외 액티브 ETF");
    await expect(page.locator("table")).toBeVisible();
    await expect(page.getByRole("cell", { name: "DYNF" })).toBeVisible();
    await expect(page.getByRole("cell", { name: "ARKK" })).toBeVisible();
    await expect(page.getByRole("cell", { name: "CGGR" })).toBeVisible();
    await expect(page.getByRole("cell", { name: "AVUV" })).toBeVisible();
  });

  test("renders compare link and pagination info", async ({ page }) => {
    await mockApi(page);
    await page.goto("/etfs");

    await expect(page.getByRole("link", { name: /비교/ }).first()).toBeVisible();
    await expect(page.locator("text=총 4개")).toBeVisible();
  });

  test("shows error state when API fails", async ({ page }) => {
    await mockApiError(page);
    await page.goto("/etfs");

    await expect(page.getByText("ETF 목록을 불러오지 못했습니다")).toBeVisible({ timeout: 10_000 });
  });
});

test.describe("ETF detail page", () => {
  test("renders ETF detail with holdings table", async ({ page }) => {
    await mockApi(page);
    await page.goto("/etfs/DYNF");

    await expect(page.locator("h1")).toContainText("DYNF", { timeout: 10_000 });
    await expect(page.getByText("BlackRock")).toBeVisible();
    // Scope to the holdings table: the change feed below lists the same tickers,
    // so an unscoped cell lookup matches two elements (strict mode violation).
    const holdingsTable = page.getByRole("table").first();
    await expect(holdingsTable.getByRole("cell", { name: "NVDA" })).toBeVisible({ timeout: 10_000 });
    await expect(holdingsTable.getByRole("cell", { name: "AAPL" })).toBeVisible();
    await expect(holdingsTable.getByRole("cell", { name: "MSFT" })).toBeVisible();
  });
});

test.describe("Changes page", () => {
  test("renders recent changes feed", async ({ page }) => {
    await mockApi(page);
    await page.goto("/changes");

    await expect(page.locator("h1")).toContainText("최근 매매 피드");
    await expect(page.getByText("NVDA")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText("TSLA")).toBeVisible();
  });

  test("shows error state when API fails", async ({ page }) => {
    await mockApiError(page);
    await page.goto("/changes");

    await expect(page.getByText("최근 매매 데이터를 불러오지 못했습니다")).toBeVisible({ timeout: 10_000 });
  });
});

test.describe("Compare page", () => {
  test("renders compare page with range selector", async ({ page }) => {
    await mockApi(page);
    await page.goto("/compare");

    await expect(page.locator("h1")).toContainText("관심 ETF 비교");
    // Range buttons should be visible
    await expect(page.getByRole("button", { name: "1Y" })).toBeVisible();
    await expect(page.getByRole("link", { name: "목록" })).toBeVisible();
  });
});
