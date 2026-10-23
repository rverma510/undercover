import { defineConfig } from "@playwright/test";
import { tmpdir } from "node:os";
import { join } from "node:path";

// The tests run on their own ports and database, so they never touch dev data.
const BACKEND_URL = "http://127.0.0.1:8100";

export default defineConfig({
  testDir: "e2e",
  outputDir: "e2e/test-results",
  reporter: "list",
  use: { baseURL: "http://localhost:5174" },
  webServer: [
    {
      command:
        "uv run -m backend.seed && uv run -m uvicorn backend.main:app --port 8100",
      url: `${BACKEND_URL}/api/health`,
      reuseExistingServer: false,
      env: { UNDERCOVER_DB: join(tmpdir(), "undercover-e2e.db") },
    },
    {
      command: "npx vite dashboard --port 5174 --strictPort",
      url: "http://localhost:5174",
      reuseExistingServer: false,
      env: { BACKEND_URL },
    },
  ],
});
