import { chromium } from '@playwright/test'
import { mkdir } from 'node:fs/promises'

const routes = ['/', '/site', '/electrical', '/chargers', '/inspect', '/solar', '/battery', '/grid', '/alarms', '/telemetry', '/graph', '/forecasts', '/dispatch', '/scenarios', '/compare', '/validation', '/health', '/stream', '/rl-lab']
const baseURL = process.env.PLAYWRIGHT_BASE_URL ?? 'http://127.0.0.1:5173'
const out = process.env.TWIN_VISUAL_OUTPUT ?? '/tmp/ev-visual-audit'
await mkdir(out, { recursive: true })
const browser = await chromium.launch({ headless: true })
const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1 })
try {
  for (const theme of ['dark', 'light']) {
    await page.goto(`${baseURL}/`)
    if (theme === 'light') await page.getByRole('button', { name: 'Switch to light theme' }).click()
    for (let index = 0; index < routes.length; index++) {
      await page.goto(`${baseURL}${routes[index]}`)
      await page.locator('.panel, .site-stage').first().waitFor({ timeout: 15000 })
      await page.screenshot({ path: `${out}/desktop-${theme}-${String(index + 1).padStart(2, '0')}.png`, fullPage: true })
    }
  }
  await page.setViewportSize({ width: 400, height: 844 })
  await page.goto(`${baseURL}/`)
  if (await page.locator('html').getAttribute('data-theme') === 'light') await page.getByRole('button', { name: 'Switch to dark theme' }).click()
  for (let index = 0; index < routes.length; index++) {
    await page.goto(`${baseURL}${routes[index]}`)
    await page.locator('.panel, .site-stage').first().waitFor({ timeout: 15000 })
    const width = await page.evaluate(() => document.documentElement.scrollWidth)
    if (width > 400) throw new Error(`${routes[index]} overflows mobile viewport: ${width}px`)
    await page.screenshot({ path: `${out}/mobile-dark-${String(index + 1).padStart(2, '0')}.png`, fullPage: true })
  }
} finally {
  await browser.close()
}
console.log(`Captured ${routes.length * 3} screen states in ${out}`)
