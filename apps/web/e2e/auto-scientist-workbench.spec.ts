import { expect, test } from "@playwright/test";

test("Auto Scientist workbench exposes tabbed workflow, job controls, and safety labels", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByRole("heading", { name: "AI-Scientist-style Research Workspace" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Auto Scientist Workbench" })).toBeVisible();
  await expect(page.getByText("generated code requires review", { exact: false })).toBeVisible();
  await expect(page.getByText("not scientific conclusions", { exact: false })).toBeVisible();

  await expect(page.getByRole("heading", { name: "Sandboxed Experiments" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Paper Writing & Review" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Trust Package & Approval" })).toBeVisible();

  await expect(page.getByRole("tab", { name: /Ideas/ })).toBeVisible();
  await expect(page.getByRole("tab", { name: /Experiments/ })).toBeVisible();
  await expect(page.getByRole("tab", { name: /Code Review/ })).toBeVisible();
  await expect(page.getByRole("tab", { name: /Paper/ })).toBeVisible();
  await expect(page.getByRole("tab", { name: /Trust/ })).toBeVisible();

  await expect(page.getByRole("button", { name: /Generate ideas/ })).toBeVisible();
  await page.getByRole("tab", { name: /Experiments/ }).click();
  await expect(page.getByRole("button", { name: /Run job/ })).toBeVisible();
  await expect(page.getByRole("button", { name: /Cancel job/ })).toBeVisible();
  await expect(page.getByText("Latest job", { exact: false })).toBeVisible();
  await expect(page.getByText("Job event timeline", { exact: false })).toBeVisible();
  await expect(page.getByText("Experiment tree nodes", { exact: false })).toBeVisible();
  await expect(page.getByRole("button", { name: /Rewrite paper from best/ })).toBeVisible();

  await page.getByRole("tab", { name: /Code Review/ }).click();
  await expect(page.getByRole("button", { name: /Create approval-gated proposal/ })).toBeVisible();
  await expect(page.getByText("Approval reason", { exact: false })).toBeVisible();
  await expect(page.getByRole("button", { name: /Rerun approved proposal/ })).toBeVisible();

  await page.getByRole("tab", { name: /Paper/ }).click();
  await expect(page.getByText("Selected experiment tree node", { exact: false })).toBeVisible();
  await expect(page.getByRole("button", { name: /Rewrite from selected\/best node/ })).toBeVisible();
  await expect(page.getByRole("button", { name: /Generate revision plan/ })).toBeVisible();
  await expect(page.getByRole("button", { name: /Apply approved patches/ })).toBeVisible();
  await expect(page.getByRole("button", { name: /Bind claims to experiments/ })).toBeVisible();
  await expect(page.getByText("Experiment claim bindings", { exact: false })).toBeVisible();
});
