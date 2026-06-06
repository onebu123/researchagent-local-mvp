import { expect, test } from "@playwright/test";

test.setTimeout(60_000);

async function closeDrawer(page: import("@playwright/test").Page) {
  await page.locator(".fixed .icon-button").first().click();
}

test("v1 local MVP dashboard groups export and readiness with mock fallback", async ({ page }) => {
  await page.route("**/api/**", (route) => route.abort());
  await page.goto("/");

  await expect(page.getByLabel("Local MVP Overview")).toBeVisible();
  await expect(page.getByText("Project Status").first()).toBeVisible();
  await expect(page.getByText("Global Trust Summary").first()).toBeVisible();
  await expect(page.getByText("Latest Manuscript Version").first()).toBeVisible();

  for (const group of ["Overview", "Manuscript", "Evidence", "Literature", "Analysis", "Audit-Export"]) {
    await expect(page.getByText(group, { exact: true }).first()).toBeVisible();
  }

  await page.getByRole("button", { name: "Project Export" }).click();
  await expect(page.getByRole("heading", { name: "Project Export" })).toBeVisible();
  await expect(page.getByText("researchagent_demo_project_local_mvp_export_mock.zip").first()).toBeVisible();
  await expect(page.getByRole("button", { name: "Generate zip" })).toBeVisible();
  await expect(page.getByText("Local MVP export only").first()).toBeVisible();
  await closeDrawer(page);

  await page.getByRole("button", { name: "Release Readiness" }).click();
  await expect(page.getByRole("heading", { name: "Release Readiness" })).toBeVisible();
  await expect(page.getByText("needs_local_review").first()).toBeVisible();
  await expect(page.getByText("No authentication").first()).toBeVisible();
  await expect(page.getByText("python scripts/validate_v1.py").first()).toBeVisible();
  await closeDrawer(page);

  await page.getByRole("button", { name: "Validate Local MVP" }).click();
  await expect(page.getByText("python scripts/validate_v1.py").first()).toBeVisible();
});
