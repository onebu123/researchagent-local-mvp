import { expect, test } from "@playwright/test";

test("v1.4 statistical assistant panel renders with mock fallback", async ({ page }) => {
  await page.route("**/api/**", (route) => route.abort());
  await page.goto("/");

  await expect(page.getByRole("button", { name: "Statistical Assistant" })).toBeVisible();
  await page.getByRole("button", { name: "Statistical Assistant" }).click();
  await expect(page.getByRole("heading", { name: "Statistical Assistant" })).toBeVisible();
  await expect(page.getByText("Variable Role Suggestions")).toBeVisible();
  await expect(page.getByText("Descriptive Cards")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Association Candidates" })).toBeVisible();
  await expect(page.getByText("outcome-candidate").first()).toBeVisible();
  await expect(page.getByText("causal_inference")).toBeVisible();
  await page.getByRole("button", { name: /Generate Local Report/ }).click();
  await expect(
    page.getByText("Statistical assistant report generated from local descriptive analysis.")
  ).toBeVisible();
});
