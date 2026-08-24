import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  timeout: 30_000,
  webServer: {
    command: "python -m uvicorn backend.main:app --host 127.0.0.1 --port 8785",
    cwd: "..",
    env: {
      APP_ENV: "production",
      DEMO_MODE: "false",
      PYTHONPATH: ".",
    },
    reuseExistingServer: true,
    timeout: 60_000,
    url: "http://127.0.0.1:8785/api/v1/ready",
  },
  use: {
    baseURL: "http://127.0.0.1:8785",
    trace: "retain-on-failure",
    viewport: { width: 1440, height: 1000 },
  },
  projects: [
    {
      name: "msedge",
      use: {
        ...devices["Desktop Edge"],
        viewport: { width: 1440, height: 1000 },
        channel: "msedge",
      },
    },
  ],
});
