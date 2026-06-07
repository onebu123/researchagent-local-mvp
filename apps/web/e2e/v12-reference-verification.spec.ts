import { expect, test } from "@playwright/test";

test.setTimeout(60_000);

async function closeDrawer(page: import("@playwright/test").Page) {
  await page.locator(".fixed .icon-button").first().click();
}

test("v1.2 reference verification panels render with mock fallback", async ({ page }) => {
  await page.route("**/api/**", (route) => route.abort());
  await page.goto("/");

  await expect(page.getByText("Reference Verification").first()).toBeVisible();

  await page.getByRole("button", { name: "Run Reference Verification" }).first().click();
  await expect(page.getByRole("heading", { name: "Reference Verification" })).toBeVisible();
  await expect(page.getByText("ref_verify_0001").first()).toBeVisible();
  await expect(page.getByText("literature_index_modified=false").first()).toBeVisible();
  await closeDrawer(page);

  await page.getByRole("button", { name: "Verification Results" }).click();
  await expect(page.getByRole("heading", { name: "Reference Verification" })).toBeVisible();
  await expect(page.getByText("needs_human_review").first()).toBeVisible();
  await closeDrawer(page);

  await page.getByRole("button", { name: "Approval Workflow" }).click();
  await expect(page.getByRole("heading", { name: "Approval Workflow" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Approve Only" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Approve and Apply" })).toBeVisible();
  await closeDrawer(page);

  await page.getByRole("button", { name: "Verified References" }).click();
  await expect(page.getByRole("heading", { name: "Verified References" })).toBeVisible();
  await expect(page.getByText("No formal References entries are available").first()).toBeVisible();
  await closeDrawer(page);

  await page.getByRole("button", { name: "Citation Grounding" }).click();
  await expect(page.getByRole("heading", { name: "Citation Grounding" })).toBeVisible();
  await expect(page.getByText("grounding_0001").first()).toBeVisible();
  await closeDrawer(page);

  await page.getByRole("button", { name: "BibTeX Status" }).click();
  await expect(page.getByRole("heading", { name: "BibTeX" })).toBeVisible();
  await expect(page.getByText("candidate_records").first()).toBeVisible();
});
