import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  timeout: 30_000,
  workers: Number.parseInt(process.env.PLAYWRIGHT_WORKERS ?? "1", 10),
  expect: {
    timeout: 8_000
  },
  use: {
    baseURL: "http://127.0.0.1:3100",
    trace: "retain-on-failure",
    video: "retain-on-failure",
    screenshot: "only-on-failure"
  },
  webServer: [
    {
      command: "python -m uvicorn main:app --host 127.0.0.1 --port 8000",
      url: "http://127.0.0.1:8000/health",
      timeout: 120_000,
      reuseExistingServer: !process.env.CI,
      cwd: "../../services/api"
    },
    {
      command: "npm run dev -- --hostname 127.0.0.1 --port 3100",
      url: "http://127.0.0.1:3100",
      timeout: 120_000,
      reuseExistingServer: !process.env.CI,
      env: {
        NEXT_PUBLIC_API_BASE_URL:
          process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000"
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
