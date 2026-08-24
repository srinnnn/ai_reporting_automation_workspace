import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  timeout: 30_000,
  use: {
    baseURL: "http://127.0.0.1:8785",
    trace: "retain-on-failure",
  },
  projects: [
    { name: "msedge", use: { ...devices["Desktop Edge"], channel: "msedge" } },
  ],
});
