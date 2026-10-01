import AxeBuilder from "@axe-core/playwright"
import { expect, type Page, test } from "@playwright/test"
import { installApiFixture } from "./api-fixture"

test.beforeEach(async ({ page }) => installApiFixture(page))

const WCAG_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"]
const SAMPLE = "public/notices-sample.csv"

async function expectAccessible(page: Page) {
  const { violations } = await new AxeBuilder({ page }).withTags(WCAG_TAGS).analyze()
  const blocking = violations.filter(
    (violation) => violation.impact === "serious" || violation.impact === "critical",
  )
  expect(blocking.map((violation) => violation.id)).toEqual([])
}

async function uploadSample(page: Page) {
  await page.emulateMedia({ reducedMotion: "reduce" })
  await page.goto("/uploads")
  await page.getByRole("radio", { name: /^(english)$/i }).check()
  await page.getByLabel(/choose file/i).setInputFiles(SAMPLE)
  const dialog = page.getByRole("dialog", { name: /new upload/i })
  await expect(dialog.getByText("notices-sample.csv")).toBeVisible()
  await expectAccessible(page)
  await dialog.getByRole("button", { name: /process 5 purchases/i }).click()
  await expect(page).toHaveURL(/\/uploads\/[\w-]+$/)
  await expect(page.getByText(/processing finished/i)).toBeVisible({ timeout: 20_000 })
}

test("goes from a csv file to a reviewed purchase and two result files", async ({
  page,
  isMobile,
}) => {
  await uploadSample(page)
  await expectAccessible(page)
  await page.getByRole("searchbox").fill("test_paper")
  await expect(page.getByRole("table").getByRole("link")).toHaveCount(1)
  await page.getByRole("table").getByRole("link").click()
  await expect(page).toHaveURL(/\/lots\/test_paper\?q=test_paper$/)
  await expect(page.getByRole("article")).toBeVisible()
  await expectAccessible(page)

  await page
    .getByRole("article")
    .getByRole("button", { name: /choose candidate/i })
    .click()
  if (isMobile) await page.getByRole("radio", { name: "Companies", exact: true }).check()
  await page
    .getByRole("region", { name: /candidates/i })
    .getByRole("button")
    .nth(1)
    .click()
  await page
    .getByRole("article")
    .getByRole("button", { name: /choose candidate/i })
    .click()
  if (isMobile) await page.getByRole("radio", { name: "Companies", exact: true }).check()
  await page.getByRole("button", { name: /compare chosen \(2\)/i }).click()
  await expect(page.getByRole("dialog", { name: /compare/i }).getByRole("table")).toBeVisible()
  await expectAccessible(page)
  await page.keyboard.press("Escape")

  await page.getByRole("button", { name: /download results/i }).click()
  const exportDialog = page.getByRole("dialog", { name: /download results/i })
  await exportDialog.getByRole("radio", { name: /only the ones you chose \(2\)/i }).check()
  const downloads: string[] = []
  page.on("download", (download) => downloads.push(download.suggestedFilename()))
  await exportDialog.getByRole("button", { name: /download 2 csv/i }).click()
  await expect
    .poll(() => [...downloads].sort())
    .toEqual(["notices-sample-products.csv", "notices-sample-suppliers.csv"])

  await page.reload()
  await expect(page.getByRole("article")).toBeVisible()
  await page.getByRole("link", { name: /purchases · notices-sample\.csv/i }).click()
  await expect(page.getByRole("searchbox")).toHaveValue("test_paper")
})

test("shows the choice, its reason, a source and the main caveat on a laptop screen", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1440, height: 900 })
  await uploadSample(page)
  await page.getByRole("table").getByRole("link").first().click()
  const grounds = page.getByRole("article")
  await expect(page.getByRole("button", { pressed: true })).toBeInViewport()
  await expect(grounds.getByRole("heading", { name: /why we recommend it/i })).toBeInViewport()
  await expect(grounds.getByText(/key thing to clarify/i)).toBeInViewport()
  await expect(grounds.getByRole("link").first()).toBeInViewport()
})

test("keeps every page within the screen width", async ({ page }) => {
  await uploadSample(page)
  for (const width of [1366, 390]) {
    await page.setViewportSize({ width, height: 800 })
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(
      width,
    )
  }
  await page.getByRole("table").getByRole("link").first().click()
  await expect(page.getByRole("article")).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(
    390,
  )
})

test("moves through companies with the keyboard", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 })
  await uploadSample(page)
  await page.getByRole("table").getByRole("link").first().click()
  const second = page
    .getByRole("region", { name: /candidates/i })
    .getByRole("button")
    .nth(1)
  const name = (await second.textContent()) ?? ""
  await second.focus()
  await page.keyboard.press("Enter")
  await expect(page.getByRole("button", { pressed: true })).toBeFocused()
  await expect(page.getByRole("article")).toContainText(name.slice(0, 12))
})
