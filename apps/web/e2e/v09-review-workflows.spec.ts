import { expect, test } from "@playwright/test";

test.setTimeout(60_000);

async function closeDrawer(page: import("@playwright/test").Page) {
  await page.locator(".fixed .icon-button").first().click();
}

test("v0.9 review workflow panels render with mock fallback", async ({ page }) => {
  await page.route("**/api/**", (route) => route.abort());
  await page.goto("/");

  await page.getByRole("button", { name: "Revision Diff Review" }).click();
  await expect(page.getByRole("heading", { name: "Revision Diff Review" })).toBeVisible();
  await expect(page.getByText("needs_evidence").first()).toBeVisible();
  await expect(page.getByText("sent_issue_001").first()).toBeVisible();
  await closeDrawer(page);

  await page.getByRole("button", { name: "Metadata Review Workflow" }).click();
  await expect(page.getByRole("heading", { name: "Metadata Review Workflow" })).toBeVisible();
  await expect(page.getByText("needs_verification").first()).toBeVisible();
  await expect(page.getByText("lit_hist_0001").first()).toBeVisible();
  await closeDrawer(page);

  await page.getByRole("button", { name: "PDF Page Review" }).click();
  await expect(page.getByRole("heading", { name: "PDF Page Review" })).toBeVisible();
  await expect(page.getByText("needs_manual_check").first()).toBeVisible();
  await expect(page.getByText("ocr_not_configured").first()).toBeVisible();
  await closeDrawer(page);

  await page.getByRole("button", { name: "Analysis Timeline" }).click();
  await expect(page.getByRole("heading", { name: "Analysis Timeline" })).toBeVisible();
  await expect(page.getByText("analysis_timeline_001").first()).toBeVisible();
  await expect(page.getByText("analysis_compare_001").first()).toBeVisible();
  await closeDrawer(page);

  await page.getByRole("button", { name: "Audit Filter Export" }).click();
  await expect(page.getByRole("heading", { name: "Audit Filter Export" })).toBeVisible();
  await expect(page.getByText("audit_filtered_export_001").first()).toBeVisible();
  await expect(page.getByText("Filtered Audit Report").first()).toBeVisible();
  await closeDrawer(page);

  await expect(page.getByTestId("audit-log-entry")).toBeVisible();
  await page.getByTestId("audit-log-entry").click();
  await expect(page.getByText("event_category=workflow").first()).toBeVisible();
  await expect(page.getByText("risk_level=low").first()).toBeVisible();
  await closeDrawer(page);

  await expect(page.getByTestId("run-history-entry")).toBeVisible();
  await page.getByTestId("run-history-entry").click();
  await expect(page.getByText("failure_diagnostics").first()).toBeVisible();
  await expect(page.getByText("recoverable").first()).toBeVisible();
  await expect(page.getByText("retry_hint").first()).toBeVisible();
});
