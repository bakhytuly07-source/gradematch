import { defineConfig } from '@playwright/test';
export default defineConfig({
  testDir: './tests', fullyParallel: false, workers: 1, retries: 0,
  timeout: 30000, expect: { timeout: 15000 }, reporter: 'list',
  outputDir: '../work/e2e/test-results',
  use: { baseURL: 'http://localhost:8091', viewport: { width: 1440, height: 1000 },
    channel: 'chromium', headless: true, trace: 'retain-on-failure' },
});
