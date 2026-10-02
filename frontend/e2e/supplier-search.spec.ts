import AxeBuilder from "@axe-core/playwright"
import { expect, type Page, test } from "@playwright/test"
import { installApiFixture } from "./api-fixture"
import { chooseLanguage } from "./language"

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

function settledWidth(page: Page): Promise<number> {
  return page.evaluate(
    () =>
      new Promise<number>((resolve) =>
        requestAnimationFrame(() =>
          requestAnimationFrame(() => resolve(document.documentElement.scrollWidth)),
        ),
      ),
  )
}

async function showView(page: Page, name: RegExp) {
  const views = page.getByRole("group", { name: /review section/i })
  if (await views.isVisible()) await views.getByRole("radio", { name }).check()
}

async function uploadSample(page: Page) {
  await page.emulateMedia({ reducedMotion: "reduce" })
  await page.goto("/uploads")
  await chooseLanguage(page, /^english$/i)
  await page.getByLabel(/choose file/i).setInputFiles(SAMPLE)
  const dialog = page.getByRole("dialog", { name: /new upload/i })
  await expect(dialog.getByText("notices-sample.csv")).toBeVisible()
  await expectAccessible(page)
  await dialog.getByRole("button", { name: /process 5 purchases/i }).click()
  await expect(page).toHaveURL(/\/uploads\/[\w-]+$/)
  await expect(page.getByText(/processing finished/i)).toBeVisible({ timeout: 20_000 })
}

test("goes from a csv file to a reviewed purchase and two result files", async ({ page }) => {
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
  await showView(page, /^candidates$/i)
  await page
    .getByRole("region", { name: /candidates/i })
    .getByRole("button")
    .nth(1)
    .click()
  await page
    .getByRole("article")
    .getByRole("button", { name: /choose candidate/i })
    .click()
  await showView(page, /^candidates$/i)
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
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible()
  await showView(page, /^grounds$/i)
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

test("keeps the decision in reach on a laptop screen", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 800 })
  await uploadSample(page)
  await page.getByRole("table").getByRole("link").first().click()
  const choose = page.getByRole("article").getByRole("button", { name: /choose candidate/i })
  await expect(choose).toBeInViewport()
  await page.mouse.move(1000, 500)
  await page.mouse.wheel(0, 400)
  await expect.poll(() => page.evaluate(() => window.scrollY)).toBeGreaterThan(0)
  await expect(choose).toBeInViewport()
})

test("opens sources in a new tab and walks to the next purchase", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 })
  await uploadSample(page)
  await page.getByRole("table").getByRole("link").first().click()
  const source = page
    .getByRole("article")
    .getByRole("link", { name: /new tab/i })
    .first()
  await expect(source).toHaveAttribute("target", "_blank")
  await page
    .getByRole("region", { name: /candidates/i })
    .getByRole("button", { name: /West Trade/ })
    .click()
  await expect(page.getByRole("article", { name: "West Trade" })).toBeVisible()
  const next = page.getByRole("link", { name: /next purchase/i })
  await next.focus()
  await page.keyboard.press("Enter")
  await expect(page).toHaveURL(/\/lots\/test_workwear/)
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("test_workwear")
})

test("keeps every page within the screen width", async ({ page }) => {
  await uploadSample(page)
  for (const width of [1366, 390]) {
    await page.setViewportSize({ width, height: 800 })
    expect(await settledWidth(page)).toBeLessThanOrEqual(width)
  }
  await page.getByRole("table").getByRole("link").first().click()
  await expect(page.getByRole("article")).toBeVisible()
  expect(await settledWidth(page)).toBeLessThanOrEqual(390)
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
