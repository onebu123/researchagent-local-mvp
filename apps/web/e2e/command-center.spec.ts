import { expect, test } from "@playwright/test";

test("ResearchAgent Command Center shows the all-in-one workflow", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByRole("heading", { name: "All-in-one Research Agent Workspace" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Project Setup" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Knowledge & Evidence Index" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Manuscript & Review Loop" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Export & Trust Report" })).toBeVisible();
});
