import { expect, test } from "@playwright/test";

test.setTimeout(60_000);

async function closeDrawer(page: import("@playwright/test").Page) {
  await page.locator(".fixed .icon-button").first().click();
}

test("v0.10 trust and readiness panels render with mock fallback", async ({ page }) => {
  await page.route("**/api/**", (route) => route.abort());
  await page.goto("/");

  await page.getByRole("button", { name: "Evidence Claim Review" }).click();
  await expect(page.getByRole("heading", { name: "Evidence Claim Review" })).toBeVisible();
  await expect(page.getByText("claim_001").first()).toBeVisible();
  await expect(page.getByText("partially_supported").first()).toBeVisible();
  await closeDrawer(page);

  await page.getByRole("button", { name: "Global Trust Dashboard" }).click();
  await expect(page.getByRole("heading", { name: "Global Trust Dashboard" })).toBeVisible();
  await expect(page.getByText("needs_review").first()).toBeVisible();
  await expect(page.getByText("run_failure_fixture_001").first()).toBeVisible();
  await closeDrawer(page);

  await page.getByRole("button", { name: "Reviewer Closure" }).click();
  await expect(page.getByRole("heading", { name: "Reviewer Closure" })).toBeVisible();
  await expect(page.getByText("sent_issue_001").first()).toBeVisible();
  await expect(page.getByText("workflow closure only").first()).toBeVisible();
  await closeDrawer(page);

  await page.getByRole("button", { name: "Metadata Revert Preview" }).click();
  await expect(page.getByRole("heading", { name: "Metadata Revert Preview" })).toBeVisible();
  await expect(page.getByText("metadata_revert_preview_001").first()).toBeVisible();
  await expect(page.getByRole("button", { name: "Preview Revert" }).first()).toBeVisible();
  await closeDrawer(page);

  await page.getByRole("button", { name: "PDF Page Text Preview" }).click();
  await expect(page.getByRole("heading", { name: "PDF Page Text Preview" })).toBeVisible();
  await expect(page.getByText("ocr_attempted=false").first()).toBeVisible();
  await expect(page.getByText("Demo PDF Literature Placeholder").first()).toBeVisible();
  await closeDrawer(page);

  await page.getByRole("button", { name: "Analysis Timeline" }).click();
  await expect(page.getByRole("heading", { name: "Analysis Timeline" })).toBeVisible();
  await expect(page.getByText("Enhanced change diagnostics").first()).toBeVisible();
  await expect(page.getByText("run_failure_fixture_001").first()).toBeVisible();
  await closeDrawer(page);

  await page.getByRole("button", { name: "v1.0 Readiness" }).click();
  await expect(page.getByRole("heading", { name: "v1.0 Readiness" })).toBeVisible();
  await expect(page.getByText("needs_local_review").first()).toBeVisible();
  await expect(page.getByText("No authentication").first()).toBeVisible();
});
