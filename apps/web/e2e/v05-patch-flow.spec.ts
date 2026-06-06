import { execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { expect, test } from "@playwright/test";

const repoRoot = path.resolve(__dirname, "..", "..", "..");
const demoProject = path.join(repoRoot, "projects", "demo_project");
const draftPath = path.join(demoProject, "manuscript", "draft.md");

function prepareDemoProject() {
  execFileSync("python", ["scripts/seed_demo.py"], { cwd: repoRoot, stdio: "pipe" });
  execFileSync("python", ["scripts/run_demo.py"], { cwd: repoRoot, stdio: "pipe" });
  fs.rmSync(path.join(demoProject, "manuscript", "patches"), { recursive: true, force: true });
  fs.rmSync(path.join(demoProject, "manuscript", "versions"), { recursive: true, force: true });
  fs.rmSync(path.join(demoProject, "reviews", "revision_decisions.jsonl"), { force: true });
}

async function closeDrawer(page: import("@playwright/test").Page) {
  await page.locator(".fixed .icon-button").first().click();
}

test("v0.5 real backend patch confirmation creates manuscript version without overwriting draft", async ({
  page
}) => {
  test.setTimeout(90_000);
  prepareDemoProject();
  const draftBefore = fs.readFileSync(draftPath, "utf-8");

  await page.goto("/");

  await expect(page.getByText("ResearchAgent v0.3")).toBeVisible();
  await page.getByRole("button", { name: "查看句子级审稿问题" }).click();
  await expect(page.getByText("sent_issue_001")).toBeVisible();
  await expect(page.getByText("revision_diff").first()).toBeVisible();
  await closeDrawer(page);

  await page.getByRole("button", { name: "查看修订建议" }).click();
  await expect(page.getByText("before").first()).toBeVisible();
  await expect(page.getByText("after").first()).toBeVisible();
  await page.getByRole("button", { name: "Accept" }).first().click();
  await expect(page.getByText("accepted").first()).toBeVisible();
  await closeDrawer(page);

  await page.getByRole("button", { name: "查看 Manuscript Patch" }).click();
  await page.getByRole("button", { name: "Generate Patch" }).click();
  await expect(page.getByText("Manuscript Patch Preview")).toBeVisible();
  await expect(page.getByText("patch_item_001").first()).toBeVisible();
  await expect(page.getByText("human confirmation required")).toBeVisible();
  await page.getByRole("button", { name: "Confirm Patch" }).click();
  await expect(page.getByText("confirmed").first()).toBeVisible();
  await closeDrawer(page);

  await page.getByRole("button", { name: "查看 Manuscript Versions" }).click();
  await expect(page.getByText(/manuscript_v\d+/).first()).toBeVisible();
  await expect(page.getByText("Evidence Checklist")).toBeVisible();
  await closeDrawer(page);

  const draftAfter = fs.readFileSync(draftPath, "utf-8");
  expect(draftAfter).toBe(draftBefore);

  await page.getByRole("button", { name: "查看审计日志" }).click();
  await expect(page.getByText("create_revision_decision").first()).toBeVisible();
  await expect(page.getByText("generate_manuscript_patch").first()).toBeVisible();
  await expect(page.getByText("create_manuscript_version").first()).toBeVisible();
  await expect(page.getByText("confirm_manuscript_patch").first()).toBeVisible();
  await closeDrawer(page);

  await page.getByRole("button", { name: "验证审计链" }).click();
  await expect(page.getByText("valid").first()).toBeVisible();
  await expect(page.getByText("local integrity aid")).toBeVisible();
  await closeDrawer(page);

  await page.getByRole("button", { name: "查看运行历史" }).click();
  await expect(page.getByText("completed").first()).toBeVisible();
});
