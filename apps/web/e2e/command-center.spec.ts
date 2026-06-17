import { expect, test } from "@playwright/test";

test("ResearchAgent Command Center shows the Auto Scientist workflow", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByRole("heading", { name: "AI-Scientist-style Research Workspace" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Research Brief & Evidence" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Idea Generation" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Sandboxed Experiments" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Paper Writing & Review" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Trust Package & Approval" })).toBeVisible();
});
