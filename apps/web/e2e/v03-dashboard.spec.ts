import { expect, test } from "@playwright/test";

async function closeDrawer(page: import("@playwright/test").Page) {
  await page.locator(".fixed .icon-button").first().click();
}

test("v0.3 dashboard panels render with mock fallback", async ({ page }) => {
  await page.route("**/api/**", (route) => route.abort());
  await page.goto("/");

  await expect(page.getByText("ResearchAgent v0.3")).toBeVisible();
  await expect(page.getByText("mock fallback", { exact: true })).toBeVisible();

  await page.getByText("论文 Markdown 初稿").click();
  await expect(page.getByText("Mock manuscript preview")).toBeVisible();
  await closeDrawer(page);

  await page.getByRole("button", { name: "查看证据链" }).click();
  await expect(page.getByText("claim_001")).toBeVisible();
  await expect(page.getByText("claim_002")).toBeVisible();
  await expect(page.getByText("claim_003")).toBeVisible();
  await closeDrawer(page);

  await page.getByRole("button", { name: "查看图表来源" }).click();
  await expect(page.getByText("mock_sha256").first()).toBeVisible();
  await closeDrawer(page);

  await page.getByRole("button", { name: "查看 Claim 对齐" }).click();
  await expect(page.getByText("align_001")).toBeVisible();
  await expect(page.getByText("claim_001")).toBeVisible();
  await closeDrawer(page);

  await page.getByRole("button", { name: "查看句子级审稿问题" }).click();
  await expect(page.getByText("sent_issue_001")).toBeVisible();
  await expect(page.getByText("discussion_over_inference")).toBeVisible();
  await closeDrawer(page);

  await page.getByRole("button", { name: "文献元数据核验" }).click();
  await expect(page.getByText("metadata_status").first()).toBeVisible();
  await expect(page.getByText("human_verified").first()).toBeVisible();
  await closeDrawer(page);

  await page.getByRole("button", { name: "查看分析来源" }).click();
  await expect(page.getByText("input_data_hash")).toBeVisible();
  await expect(page.getByText("mock_sha256")).toBeVisible();
});
