import { expect, test } from "@playwright/test";

async function closeDrawer(page: import("@playwright/test").Page) {
  await page.locator(".fixed .icon-button").first().click();
}

test("v0.6 dashboard entries render with mock fallback", async ({ page }) => {
  await page.route("**/api/**", (route) => route.abort());
  await page.goto("/");

  await expect(page.getByText("编辑 Patch Item")).toBeVisible();
  await page.getByRole("button", { name: "编辑 Patch Item" }).click();
  await expect(page.getByText("Latest Safety Result")).toBeVisible();
  await closeDrawer(page);

  await page.getByRole("button", { name: "检查 Patch 冲突" }).click();
  await expect(page.getByText("conflict_001")).toBeVisible();
  await closeDrawer(page);

  await page.getByRole("button", { name: "合并 Patch 预览" }).click();
  await expect(page.getByText("merge_001", { exact: true }).first()).toBeVisible();
  await closeDrawer(page);

  await page.getByRole("button", { name: "查看 Manuscript Diff" }).click();
  await expect(page.getByText("diff_001", { exact: true }).first()).toBeVisible();
  await closeDrawer(page);

  await page.getByRole("button", { name: "查看 Issue Resolution" }).click();
  await expect(page.getByText("sent_issue_001").first()).toBeVisible();
  await closeDrawer(page);

  await page.getByRole("button", { name: "导出 Audit Report" }).click();
  await expect(page.getByText("audit_export_001", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("production-grade tamper-proof").first()).toBeVisible();
});
