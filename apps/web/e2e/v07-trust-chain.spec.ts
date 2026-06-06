import { expect, test } from "@playwright/test";

async function closeDrawer(page: import("@playwright/test").Page) {
  await page.locator(".fixed .icon-button").first().click();
}

test("v0.7 trust chain panels render with mock fallback", async ({ page }) => {
  await page.route("**/api/**", (route) => route.abort());
  await page.goto("/");

  await page.getByRole("button", { name: "Version Lineage" }).click();
  await expect(page.getByRole("heading", { name: "Version Lineage" })).toBeVisible();
  await expect(page.getByText("generated_version").first()).toBeVisible();
  await closeDrawer(page);

  await page.getByRole("button", { name: /Patch 预览/ }).click();
  await expect(page.getByText("merge_001", { exact: true }).first()).toBeVisible();
  await page.getByRole("button", { name: "Confirm Version" }).click();
  await expect(page.getByText("generated_version").first()).toBeVisible();
  await expect(page.getByText("manuscript_v001").first()).toBeVisible();
  await closeDrawer(page);

  await page.getByRole("button", { name: /Issue Resolution/ }).click();
  await expect(page.getByText("human_reviews").first()).toBeVisible();
  await expect(page.getByRole("button", { name: "Resolved" }).first()).toBeVisible();
  await expect(page.getByRole("button", { name: "Review" }).first()).toBeVisible();
  await closeDrawer(page);

  await page.getByRole("button", { name: /Audit Report/ }).click();
  await expect(page.getByText("File Manifest").first()).toBeVisible();
  await expect(page.getByText("mock_draft_sha256").first()).toBeVisible();
});
