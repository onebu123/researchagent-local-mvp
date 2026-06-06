import { expect, test } from "@playwright/test";

async function closeDrawer(page: import("@playwright/test").Page) {
  await page.locator(".fixed .icon-button").first().click();
}

test("v0.8 quality and diff panels render with mock fallback", async ({ page }) => {
  await page.route("**/api/**", (route) => route.abort());
  await page.goto("/");

  await page.getByRole("button", { name: "精细 Revision Diff" }).click();
  await expect(page.getByRole("heading", { name: "Revision Line Diff" })).toBeVisible();
  await expect(page.getByText("revision_diff_001").first()).toBeVisible();
  await expect(page.getByText("line_start").first()).toBeVisible();
  await closeDrawer(page);

  await page.getByRole("button", { name: "Metadata 字段 Diff" }).click();
  await expect(page.getByRole("heading", { name: "Metadata Field Diff" })).toBeVisible();
  await expect(page.getByText("lit_hist_0001").first()).toBeVisible();
  await expect(page.getByRole("button", { name: "Suggest Revert" }).first()).toBeVisible();
  await closeDrawer(page);

  await page.getByRole("button", { name: "批量审阅 Metadata" }).click();
  await expect(page.getByRole("heading", { name: "Metadata Batch Review" })).toBeVisible();
  await expect(page.getByText("manual_review_required").first()).toBeVisible();
  await closeDrawer(page);

  await page.getByRole("button", { name: "PDF 质量报告" }).click();
  await expect(page.getByRole("heading", { name: "PDF Quality Report" })).toBeVisible();
  await expect(page.getByText("ocr_not_configured").first()).toBeVisible();
  await closeDrawer(page);

  await page.getByRole("button", { name: "Analysis 运行对比" }).click();
  await expect(page.getByRole("heading", { name: "Analysis Comparison" })).toBeVisible();
  await expect(page.getByText("analysis_compare_001").first()).toBeVisible();
  await expect(page.getByText("input_data_hash").first()).toBeVisible();
  await closeDrawer(page);

  await page.getByRole("button", { name: "查看审计日志" }).click();
  await expect(page.getByText("event_category=workflow").first()).toBeVisible();
  await expect(page.getByText("risk_level=low").first()).toBeVisible();
  await closeDrawer(page);

  await page.getByRole("button", { name: "查看运行历史" }).click();
  await expect(page.getByText("failure_diagnostics").first()).toBeVisible();
  await expect(page.getByText("recoverable").first()).toBeVisible();
  await expect(page.getByText("retry_hint").first()).toBeVisible();
});
