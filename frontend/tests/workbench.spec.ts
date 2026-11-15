import { test, expect } from '@playwright/test'

const routes = [
  ['/', 'Command Center'],
  ['/site', '3D Site Twin'],
  ['/electrical', 'Electrical One-Line'],
  ['/chargers', 'Charger Fleet & Queue'],
  ['/inspect', 'Charger Inspection'],
  ['/solar', 'Solar Production'],
  ['/battery', 'Battery State'],
  ['/grid', 'Grid & Transformer'],
  ['/alarms', 'Alarm Triage'],
  ['/telemetry', 'Telemetry Pipeline'],
  ['/stream', 'Simulated MQTT Stream'],
  ['/graph', 'Ontology & Graph'],
  ['/forecasts', 'Forecasts'],
  ['/dispatch', 'Dispatch Optimizer'],
  ['/scenarios', 'Scenario Builder'],
  ['/compare', 'Scenario Comparison'],
  ['/rl-lab', 'PowerWise RL Lab'],
  ['/validation', 'KPI Validation'],
  ['/health', 'Architecture & Health'],
] as const

test('all 19 screens load SOFIE history in dark and light themes', async ({ page }) => {
  const errors: string[] = []
  page.on('pageerror', (error) => errors.push(error.message))
  await page.goto('/')
  await expect(page.getByText('Historical replay').first()).toBeVisible()
  await expect(page.getByText('2.92 kW').first()).toBeVisible()
  for (const [path, title] of routes) {
    await page.goto(path)
    await expect(page.getByRole('heading', { name: title, exact: true })).toBeVisible()
    await expect(page.getByText('Loading verified SOFIE history…')).toHaveCount(0)
    await expect(page.getByText('Data could not be loaded.')).toHaveCount(0)
  }
  await page.goto('/')
  await expect(page.getByText('2.92 kW').first()).toBeVisible()
  await page.screenshot({ path: '/tmp/ev-command-dark.png', fullPage: true })
  await page.getByRole('button', { name: 'Switch to light theme' }).click()
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'light')
  await page.screenshot({ path: '/tmp/ev-command-light.png', fullPage: true })
  expect(errors).toEqual([])
})

test('RL lab shows held-out results and both replay clocks', async ({ page }) => {
  await page.goto('/rl-lab')
  await expect(page.getByRole('heading', { name: 'What the test found' })).toBeVisible()
  await expect(page.getByText(/served .*observed EV demand/)).toBeVisible()
  await expect(page.getByText('Simulated RL test')).toBeVisible()
  await expect(page.getByText('No battery commands were sent.')).toBeVisible()
  const day = page.getByRole('combobox', { name: 'Recorded day' })
  await day.selectOption({ index: 0 })
  const selectedDay = await day.inputValue()
  await expect(page.getByRole('rowheader', { name: new RegExp(selectedDay) }).first()).toBeVisible()
  await expect(page.getByRole('columnheader', { name: 'Simulated clock' })).toBeVisible()
})

test('fleet investigation, islanded grid, and mobile navigation', async ({ page }) => {
  await page.goto('/chargers')
  await expect(page.getByRole('rowheader', { name: 'WB8' }).first()).toBeVisible()
  await page
    .locator('.content-grid .panel')
    .first()
    .getByRole('row', { name: /WB3/ })
    .getByRole('button', { name: 'Inspect' })
    .click()
  await expect(page.getByRole('heading', { name: 'WB3 · recorded state' })).toBeVisible()
  await page.goto('/grid')
  await expect(page.getByText('No utility grid connection')).toBeVisible()
  await page.goto('/graph')
  await page.getByText('Browse graph assets as a list').click()
  await page.locator('.graph-asset-list').getByRole('button', { name: /WB3/ }).click()
  await expect(page.getByRole('heading', { name: 'WB3 · recorded state' })).toBeVisible()
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/')
  await page.getByRole('button', { name: 'Open navigation' }).click()
  await expect(page.locator('.mobile-close')).toBeFocused()
  await page.keyboard.press('Escape')
  await expect(page.getByRole('button', { name: 'Open navigation' })).toBeFocused()
  await page.getByRole('button', { name: 'Open navigation' }).click()
  await page.getByRole('button', { name: 'Solar Production' }).click()
  await expect(page.getByRole('heading', { name: 'Solar Production', exact: true })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Solar production', exact: true })).toBeVisible()
  const width = await page.evaluate(() => document.documentElement.scrollWidth)
  expect(width).toBeLessThanOrEqual(390)
  await page.screenshot({ path: '/tmp/ev-solar-mobile.png', fullPage: true })
})

test('two historical scenarios can be solved and compared', async ({ page }) => {
  await page.goto('/scenarios')
  await expect(page.getByText('Scenario inputs')).toBeVisible()
  await page.locator('#scenario-start').fill('2026-06-29T13:45')
  await page.getByRole('button', { name: 'Evaluate scenario A' }).click()
  await expect(page.getByText('Last run')).toBeVisible()
  await page.getByRole('button', { name: 'Run as B' }).click()
  await page.getByLabel('Measured PV multiplier').fill('50')
  await page.getByRole('button', { name: 'Evaluate scenario B' }).click()
  await page.getByRole('button', { name: 'Compare runs' }).click()
  await expect(page.getByText('Scenario A').first()).toBeVisible()
  await expect(page.getByText('Scenario B').first()).toBeVisible()
  await expect(page.getByRole('rowheader', { name: 'unserved ev kwh' })).toBeVisible()
})

test('a scenario saves locally without sign-in and leaves an audit event', async ({ page }) => {
  await page.goto('/scenarios')
  await page.locator('#scenario-start').fill('2026-06-29T13:45')
  await page.getByRole('button', { name: 'Evaluate scenario A' }).click()
  await expect(page.getByText('Last run')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Sign in' })).toHaveCount(0)
  await page.getByRole('button', { name: 'Save with audit trail' }).click()
  await expect(page.getByText('Run saved.')).toBeVisible()
  await page.getByRole('button', { name: 'Architecture & Health' }).click()
  await expect(page.getByText('scenario.save').first()).toBeVisible()
  await page.getByRole('button', { name: 'Scenario Comparison' }).click()
  await page.reload()
  await page.getByRole('button', { name: 'Use as A' }).first().click()
  await page.getByRole('button', { name: 'Use as B' }).first().click()
  await expect(page.getByRole('rowheader', { name: 'unserved ev kwh' })).toBeVisible()
})

test('recorded alarm review works without sign-in and leaves an audit event', async ({ page }) => {
  await page.goto('/alarms')
  await page.locator('#replay-time').fill('2026-06-15T05:41')
  const open = page.getByRole('row', { name: /Open in review/ }).first()
  await expect(open).toBeVisible()
  await open.getByRole('button', { name: 'Inspect' }).click()
  await expect(page.getByRole('button', { name: 'Acknowledge in audit trail' })).toBeEnabled()
  await page.getByLabel('Operator note').fill('Reviewed historical source event in browser test')
  await page.getByRole('button', { name: 'Acknowledge in audit trail' }).click()
  await expect(page.getByText('Acknowledged by local').first()).toBeVisible()
  await page.getByRole('button', { name: 'Architecture & Health' }).click()
  await expect(page.getByText('alarm.acknowledge').first()).toBeVisible()
})

test('replay controls preserve source time in a shareable URL', async ({ page }) => {
  await page.goto('/')
  const clock = page.locator('#replay-time')
  await expect(clock).toHaveValue('2026-06-29T13:45')
  await page.getByRole('button', { name: 'Next 15 minutes' }).click()
  await expect(clock).toHaveValue('2026-06-29T14:00')
  await expect(page).toHaveURL(/at=2026-06-29T14%3A00/)
  await page.reload()
  await expect(clock).toHaveValue('2026-06-29T14:00')
  await page.getByRole('button', { name: 'Previous 15 minutes' }).click()
  await expect(clock).toHaveValue('2026-06-29T13:45')
})

test('simulated stream explains source and broker status', async ({ page }) => {
  await page.route('**/api/site', (route) =>
    route.fulfill({ status: 503, body: 'Replay history unavailable' }),
  )
  await page.goto('/stream')
  await expect(
    page.getByRole('heading', { name: 'Simulated MQTT Stream', exact: true }),
  ).toBeVisible()
  await expect(page.getByText('Historical data, simulated transport')).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Ingestion checks' })).toBeVisible()
  await expect(page.getByText('Data could not be loaded.')).toHaveCount(0)
})
