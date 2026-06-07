import { defineConfig, devices } from "@playwright/test";

const apiPort = process.env.PLAYWRIGHT_API_PORT ?? "8000";
const webPort = process.env.PLAYWRIGHT_WEB_PORT ?? "3100";
const reuseExistingServer = process.env.PLAYWRIGHT_ISOLATED_SERVER === "1" ? false : !process.env.CI;
const webCommand =
  process.env.PLAYWRIGHT_WEB_COMMAND ?? `npm run dev -- --hostname 127.0.0.1 --port ${webPort}`;

export default defineConfig({
  testDir: "./e2e",
  timeout: 30_000,
  workers: Number.parseInt(process.env.PLAYWRIGHT_WORKERS ?? "1", 10),
  expect: {
    timeout: 8_000
  },
  use: {
    baseURL: `http://127.0.0.1:${webPort}`,
    trace: "retain-on-failure",
    video: "retain-on-failure",
    screenshot: "only-on-failure"
  },
  webServer: [
    {
      command: `python -m uvicorn main:app --host 127.0.0.1 --port ${apiPort}`,
      url: `http://127.0.0.1:${apiPort}/health`,
      timeout: 120_000,
      reuseExistingServer,
      cwd: "../../services/api"
    },
    {
      command: webCommand,
      url: `http://127.0.0.1:${webPort}`,
      timeout: 120_000,
      reuseExistingServer,
      env: {
        NEXT_PUBLIC_API_BASE_URL:
          process.env.NEXT_PUBLIC_API_BASE_URL ?? `http://127.0.0.1:${apiPort}`
      }
    }
  ],
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] }
    }
  ]
});
