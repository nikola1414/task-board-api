import { defineConfig } from '@playwright/test'

// Needs the API running on :8000 (`docker compose up` in the repo root).
export default defineConfig({
  testDir: 'e2e',
  use: { baseURL: 'http://localhost:5173' },
  webServer: { command: 'npm run dev', url: 'http://localhost:5173', reuseExistingServer: true },
})
