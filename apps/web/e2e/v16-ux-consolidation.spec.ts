import { expect, test } from "@playwright/test";

test("v1.6 UX consolidation keeps core actions visible with mock fallback", async ({ page }) => {
  await page.route("**/api/**", (route) => route.abort());
  await page.goto("/");

  await expect(page.getByTestId("ux-consolidation-panel")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Workspace Readiness" })).toBeVisible();
  await expect(page.getByText("Fallback mode active")).toBeVisible();
  await expect(page.getByText("Demo remains usable without API or network")).toBeVisible();
  await expect(page.getByText("v1.6 UX consolidation")).toBeVisible();

  for (const action of [
    "Open Global Trust",
    "Review RAG Quality",
    "Open Statistical Assistant",
    "Open Workspace Export"
  ]) {
    await expect(page.getByText(action)).toBeVisible();
  }

  await page.getByTestId("ux-action-review-rag-quality").click();
  await expect(page.getByRole("heading", { name: "RAG Quality" })).toBeVisible();
  await page.locator(".fixed .icon-button").first().click();

  await page.getByTestId("ux-action-open-workspace-export").click();
  await expect(page.getByRole("heading", { name: "Workspace Export" })).toBeVisible();
  await expect(page.getByText("exports/workspace/workspace_export_manifest.json").first()).toBeVisible();
});
