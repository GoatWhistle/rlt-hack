import { defineConfig, devices } from "@playwright/test"

const baseURL = process.env.E2E_BASE_URL ?? "http://127.0.0.1:8080"

// biome-ignore lint/style/noDefaultExport: Playwright reads its configuration from the default export
export default defineConfig({
  testDir: "./e2e/live",
  testMatch: "**/*.live.ts",
  workers: 1,
  timeout: 180_000,
  reporter: [["list"]],
  use: { baseURL, trace: "retain-on-failure", acceptDownloads: true },
  projects: [{ name: "desktop", use: { ...devices["Desktop Chrome"] } }],
})
