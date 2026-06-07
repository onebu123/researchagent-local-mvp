import { expect, test } from "@playwright/test";

test.setTimeout(60_000);

async function closeDrawer(page: import("@playwright/test").Page) {
  await page.locator(".fixed .icon-button").first().click();
}

test("v1.1 literature intelligence panels render with mock fallback", async ({ page }) => {
  await page.route("**/api/**", (route) => route.abort());
  await page.goto("/");

  await expect(page.getByText("Literature Intelligence").first()).toBeVisible();

  await page.getByRole("button", { name: "LLM Settings" }).click();
  await expect(page.getByRole("heading", { name: "LLM Settings" })).toBeVisible();
  await expect(page.getByText("api_key_configured").first()).toBeVisible();
  await expect(page.getByText("literature_answer_v1").first()).toBeVisible();
  await closeDrawer(page);

  await page.getByRole("button", { name: "Literature RAG" }).click();
  await expect(page.getByRole("heading", { name: "Literature RAG" })).toBeVisible();
  await expect(page.getByText("chunk_lit_001_0001").first()).toBeVisible();
  await expect(page.getByRole("button", { name: "Ask" })).toBeVisible();
  await closeDrawer(page);

  await page.getByRole("button", { name: "Source Passage Evidence" }).click();
  await expect(page.getByRole("heading", { name: "Source Passage Evidence" })).toBeVisible();
  await expect(page.getByText("source_passage_0001").first()).toBeVisible();
  await closeDrawer(page);

  await page.getByRole("button", { name: "Metadata Lookup" }).click();
  await expect(page.getByRole("heading", { name: "Metadata Lookup" })).toBeVisible();
  await expect(page.getByText("metadata_lookup_0001").first()).toBeVisible();
  await closeDrawer(page);

  await page.getByRole("button", { name: "BibTeX", exact: true }).click();
  await expect(page.getByRole("heading", { name: "BibTeX" })).toBeVisible();
  await expect(page.getByText("Skipped lit_001").first()).toBeVisible();
  await closeDrawer(page);

  await page.getByRole("button", { name: "Citation Support" }).click();
  await expect(page.getByRole("heading", { name: "Citation Support" })).toBeVisible();
  await expect(page.getByText("claim_001").first()).toBeVisible();
  await closeDrawer(page);

  await page.getByRole("button", { name: "LLM Call Log" }).click();
  await expect(page.getByRole("heading", { name: "LLM Call Log" })).toBeVisible();
  await expect(page.getByText("llm_call_0001").first()).toBeVisible();
});
