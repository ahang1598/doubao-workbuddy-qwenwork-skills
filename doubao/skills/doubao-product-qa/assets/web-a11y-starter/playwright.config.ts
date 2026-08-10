import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './tests',
  outputDir: 'artifacts/test-results',
  reporter: [['list'], ['html', { outputFolder: 'artifacts/playwright-report', open: 'never' }], ['junit', { outputFile: 'artifacts/junit.xml' }]],
  use: {
    baseURL: process.env.QA_BASE_URL,
    trace: 'retain-on-failure',
    video: 'off',
    screenshot: process.env.QA_CAPTURE_SCREENSHOTS === '1' ? 'only-on-failure' : 'off',
  },
})
