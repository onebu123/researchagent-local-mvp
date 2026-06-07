import { expect, test } from "@playwright/test";

async function closeDrawer(page: import("@playwright/test").Page) {
  await page.getByRole("button", { name: /Close/ }).click();
}

test("v1.3 RAG quality panel renders with mock fallback", async ({ page }) => {
  await page.route("**/api/**", (route) => route.abort());
  await page.goto("/");

  await expect(page.getByRole("button", { name: "RAG Quality" })).toBeVisible();
  await page.getByRole("button", { name: "RAG Quality" }).click();
  await expect(page.getByRole("heading", { name: "RAG Quality" })).toBeVisible();
  await expect(page.getByText("hit_at_1")).toBeVisible();
  await expect(page.getByText("chunk_lit_001_0001").first()).toBeVisible();
  await expect(page.getByRole("button", { name: /Run Retrieval Eval/ })).toBeVisible();
  await page.getByRole("button", { name: /Run Retrieval Eval/ }).click();
  await expect(page.getByText("RAG retrieval eval completed with local deterministic cases.")).toBeVisible();
  await closeDrawer(page);

  await page.getByRole("button", { name: "Literature RAG" }).click();
  await expect(page.getByRole("heading", { name: "Literature RAG" })).toBeVisible();
  await expect(page.getByText("local_hybrid")).toBeVisible();
});
