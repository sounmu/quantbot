import { test, expect } from "@playwright/test";
import { mockApi, mockApiError } from "./fixtures";

test.describe("ETF list page", () => {
  test("renders ETF cards with seeded data", async ({ page }) => {
    await mockApi(page);
    await page.goto("/etfs");

    await expect(page.locator("h1")).toContainText("해외 액티브 ETF");
    await expect(page.getByRole("link", { name: "DYNF 상세 보기" })).toBeVisible();
    await expect(page.getByRole("link", { name: "ARKK 상세 보기" })).toBeVisible();
    await expect(page.getByRole("link", { name: "CGGR 상세 보기" })).toBeVisible();
    await expect(page.getByRole("link", { name: "AVUV 상세 보기" })).toBeVisible();
    await expectNoHorizontalScroll(page);
  });

  test("renders bottom tabs and pagination info", async ({ page }) => {
    await mockApi(page);
    await page.goto("/etfs");

    const bottomTabs = page.getByRole("navigation", { name: "주요 화면" });
    await expect(bottomTabs).toBeVisible();
    await expect(bottomTabs.getByRole("link", { name: "목록" })).toBeVisible();
    await expect(bottomTabs.getByRole("link", { name: "피드" })).toBeVisible();
    await expect(bottomTabs.getByRole("link", { name: "분석" })).toBeVisible();
    await expect(bottomTabs.getByRole("link", { name: "비교" })).toBeVisible();
    await expect(page.locator("text=총 4개")).toBeVisible();
    await expectNoHorizontalScroll(page);
  });

  test("shows error state when API fails", async ({ page }) => {
    await mockApiError(page);
    await page.goto("/etfs");

    await expect(page.getByText("ETF 목록을 불러오지 못했습니다")).toBeVisible({ timeout: 10_000 });
  });
});

test.describe("ETF detail page", () => {
  test("renders ETF detail with holdings cards", async ({ page }) => {
    await mockApi(page);
    await page.goto("/etfs/DYNF");

    await expect(page.locator("h1")).toContainText("DYNF", { timeout: 10_000 });
    await expect(page.getByText("BlackRock")).toBeVisible();
    await expect(page.getByRole("button", { name: /NVDA 포지션 선택/ })).toBeVisible({
      timeout: 10_000,
    });
    await expect(page.getByRole("button", { name: /AAPL 포지션 선택/ })).toBeVisible();
    await expect(page.getByRole("button", { name: /MSFT 포지션 선택/ })).toBeVisible();
    await expect(page.getByText("JPMORGAN CHASE & CO")).toHaveCount(0);
    await page.getByRole("button", { name: "더보기 1개" }).click();
    await expect(page.getByText("JPMORGAN CHASE & CO")).toBeVisible();
    await expectNoHorizontalScroll(page);
  });
});

test.describe("Changes page", () => {
  test("renders recent changes feed", async ({ page }) => {
    await mockApi(page);
    await page.goto("/changes");

    await expect(page.locator("h1")).toContainText("최근 매매 피드");
    // 모바일 카드는 종목 티커를 heading으로 노출(데스크탑 테이블 셀은 hidden이라 role 쿼리에서 제외)
    await expect(page.getByRole("heading", { name: "NVDA" })).toBeVisible({ timeout: 10_000 });
    await expect(page.getByRole("heading", { name: "TSLA" })).toBeVisible();
    await expectNoHorizontalScroll(page);
  });

  test("shows error state when API fails", async ({ page }) => {
    await mockApiError(page);
    await page.goto("/changes");

    await expect(page.getByText("최근 매매 데이터를 불러오지 못했습니다")).toBeVisible({ timeout: 10_000 });
  });
});

test.describe("Analysis page", () => {
  test("renders performance summary and conviction board", async ({ page }) => {
    await mockApi(page);
    await page.goto("/analysis");

    await expect(page.locator("h1")).toContainText("분석");
    await expect(page.getByText("컨빅션 검증")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText("Hit rate")).toBeVisible();
    await expect(page.getByText("컨빅션 보드")).toBeVisible();
    await expect(page.getByText("NVDA").first()).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText("NVIDIA CORP").first()).toBeVisible();
    await expect(page.getByText("누가 샀나")).toBeVisible();
    await expectNoHorizontalScroll(page);
  });
});

test.describe("Compare page", () => {
  test("renders compare page with range selector", async ({ page }) => {
    await mockApi(page);
    await page.goto("/compare");

    await expect(page.locator("h1")).toContainText("관심 ETF 비교");
    // Range buttons should be visible
    await expect(page.getByRole("button", { name: "1Y" })).toBeVisible();
    await expect(page.getByRole("main").getByRole("link", { name: "목록" })).toBeVisible();
    await expectNoHorizontalScroll(page);
  });
});

async function expectNoHorizontalScroll(page: import("@playwright/test").Page) {
  await expect
    .poll(() =>
      page.evaluate(
        () =>
          document.documentElement.scrollWidth <= window.innerWidth &&
          document.body.scrollWidth <= window.innerWidth
      )
    )
    .toBe(true);
}
