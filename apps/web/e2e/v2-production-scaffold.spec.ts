import { expect, test } from "@playwright/test";

test("v2.0 Research Workspace scaffold renders with mock fallback", async ({ page }) => {
  await page.route("**/api/**", (route) => route.abort());
  await page.goto("/");

  await expect(page.getByRole("heading", { name: "Research Workspace Scaffold" })).toBeVisible();
  await expect(page.getByText("v2.0 adds optional PostgreSQL")).toBeVisible();
  await expect(page.getByText("mock scaffold fallback")).toBeVisible();
  await expect(page.getByTestId("v2-capability-database")).toBeVisible();
  await expect(page.getByText("sqlite").first()).toBeVisible();
  await expect(page.getByTestId("v2-capability-task_queue")).toBeVisible();
  await expect(page.getByText("inline").first()).toBeVisible();
  await expect(page.getByTestId("v2-capability-auth")).toBeVisible();
  await expect(page.getByText("disabled").first()).toBeVisible();
  await expect(page.getByText("python scripts/validate_v2.py")).toBeVisible();
  await expect(page.getByText("API key required: no")).toBeVisible();
  await expect(page.getByText("External network required: no")).toBeVisible();
});
