import { expect, test } from "@playwright/test";

test("v1.5 workspace export panel renders with mock fallback", async ({ page }) => {
  await page.route("**/api/**", (route) => route.abort());
  await page.goto("/");

  await expect(page.getByRole("button", { name: "Workspace Export" })).toBeVisible();
  await page.getByRole("button", { name: "Workspace Export" }).click();
  await expect(page.getByRole("heading", { name: "Workspace Export" })).toBeVisible();
  await expect(page.getByText("exports/workspace/research_workspace_export.docx")).toBeVisible();
  await expect(page.getByText("exports/workspace/research_workspace_export.tex")).toBeVisible();
  await expect(page.getByText("exports/workspace/trust_report.json")).toBeVisible();
  await expect(page.getByText("exports/workspace/workspace_export_manifest.json").first()).toBeVisible();
  await expect(page.getByText("not scientific or compliance validation")).toBeVisible();
  await page.getByRole("button", { name: /Generate docs/ }).click();
  await expect(page.getByText(/Workspace export created:/)).toBeVisible();
});
