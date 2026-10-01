import AxeBuilder from "@axe-core/playwright"
import { expect, type Page, test } from "@playwright/test"
import { installApiFixture } from "./api-fixture"
import { chooseLanguage } from "./language"
import { installSearchFixture } from "./search-fixture"

test.beforeEach(async ({ page }) => {
  await installApiFixture(page)
  await installSearchFixture(page)
})

const WCAG_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"]
const QUERY = "Buckwheat groats 500 kg; polished rice 200 kg"

async function expectAccessible(page: Page) {
  const { violations } = await new AxeBuilder({ page }).withTags(WCAG_TAGS).analyze()
  const blocking = violations.filter(
    (violation) => violation.impact === "serious" || violation.impact === "critical",
  )
  expect(blocking.map((violation) => violation.id)).toEqual([])
}

async function expectWithinScreen(page: Page) {
  const width = page.viewportSize()?.width ?? 0
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(
    width,
  )
}

async function showView(page: Page, name: RegExp) {
  const views = page.getByRole("group", { name: /result section|раздел результата/i })
  if (await views.isVisible()) await views.getByRole("radio", { name }).check()
}

async function openSearch(page: Page) {
  await page.emulateMedia({ reducedMotion: "reduce" })
  await page.goto("/search")
  await chooseLanguage(page, /^english$/i)
  await expect(page.getByRole("heading", { level: 1, name: /find suppliers/i })).toBeVisible()
}

test("finds suppliers from a description and keeps the result at its address", async ({
  page,
}) => {
  await openSearch(page)
  await expectAccessible(page)
  const field = page.getByRole("textbox", { name: /describe what you need/i })
  await field.fill(QUERY)
  await field.press("Enter")
  await expect(page).toHaveURL(/\/search\/[\w-]+$/)
  await expect(page.getByRole("heading", { level: 1, name: QUERY })).toBeVisible()

  await showView(page, /^candidates$/i)
  const candidates = page.getByRole("region", { name: /^candidates/i })
  await expect(candidates.getByRole("button", { pressed: true })).toBeVisible()
  await candidates.getByRole("button", { name: /Зерновой Двор/ }).click()
  const grounds = page.getByRole("article", { name: /Зерновой Двор/ })
  await expect(grounds).toBeVisible()
  await expect(grounds.getByText(/no inn: the company cannot be identified/i)).toBeVisible()
  await expect(grounds.getByRole("heading", { name: /match for every item/i })).toBeVisible()
  await expectAccessible(page)
  await expectWithinScreen(page)

  const address = page.url()
  await chooseLanguage(page, /^русский$/i)
  await expect(
    page.getByRole("article").getByText(/Совпадение по каждой позиции/),
  ).toBeVisible()
  await page.reload()
  expect(page.url()).toBe(address)
  await expect(page.getByRole("heading", { level: 1, name: QUERY })).toBeVisible()
  await showView(page, /^основания$/i)
  await expect(page.getByRole("article", { name: /Зерновой Двор/ })).toBeVisible()
  await expect(page.getByRole("link", { name: /^поиск$/i })).toHaveAttribute(
    "aria-current",
    "page",
  )
})

test("opens a company profile and returns to a recent search", async ({ page }) => {
  await openSearch(page)
  await page.getByRole("button", { name: /office paper a4/i }).click()
  await expect(page).toHaveURL(/\/search\/[\w-]+$/)
  await expect(page.getByRole("note", { name: /may be incomplete/i })).toBeVisible()
  await page.getByRole("button", { name: /company profile/i }).click()
  const profile = page.getByRole("dialog", { name: /Северный Провиант/ })
  await expect(profile.getByText(/current offers/i)).toBeVisible()
  await expectAccessible(page)
  await page.keyboard.press("Escape")

  await page.getByRole("link", { name: /new search/i }).click()
  const recent = page.getByRole("region", { name: /recent searches/i })
  await recent.getByRole("link", { name: /office paper/i }).click()
  await expect(page).toHaveURL(/\/search\/[\w-]+$/)
  await expectWithinScreen(page)
})

test("chooses a candidate and downloads the choice", async ({ page }) => {
  await openSearch(page)
  const field = page.getByRole("textbox", { name: /describe what you need/i })
  await field.fill(QUERY)
  await field.press("Enter")
  await expect(page).toHaveURL(/\/search\/[\w-]+$/)
  await showView(page, /^candidates$/i)
  await page
    .getByRole("region", { name: /^candidates/i })
    .getByRole("button", { name: /Зерновой Двор/ })
    .click()
  await expect(page).toHaveURL(/candidate=/)
  const grounds = page.getByRole("article", { name: /Зерновой Двор/ })
  await grounds.getByRole("button", { name: /choose candidate/i }).click()
  await expect(grounds.getByRole("button", { name: /remove from chosen/i })).toBeVisible()
  await page.reload()
  await expect(page.getByRole("heading", { level: 1, name: QUERY })).toBeVisible()
  await showView(page, /^candidates$/i)
  const card = page
    .getByRole("region", { name: /^candidates/i })
    .getByRole("button", { name: /Зерновой Двор/ })
  await expect(card.getByText(/^chosen$/i)).toBeVisible()
  await page.getByRole("button", { name: /download csv/i }).click()
  const dialog = page.getByRole("dialog", { name: /download candidates/i })
  await expect(
    dialog.getByRole("radio", { name: /only the ones you chose \(1\)/i }),
  ).toBeChecked()
  await expectAccessible(page)
  const download = page.waitForEvent("download")
  await dialog.getByRole("button", { name: /download csv/i }).click()
  expect((await download).suggestedFilename()).toMatch(/^search-.+-suppliers\.csv$/)
  await expect(page.getByText(/file downloaded/i)).toBeVisible()
})

test("explains an empty result and a query it cannot read", async ({ page }) => {
  await openSearch(page)
  const field = page.getByRole("textbox", { name: /describe what you need/i })
  await field.fill("123 !!!")
  await field.press("Enter")
  await expect(page.getByRole("alert")).toContainText(/could not pick out any items/i)
  await field.fill("Tractor tyres 4 pcs")
  await field.press("Control+Enter")
  await expect(page.getByRole("heading", { name: /no suppliers found/i })).toBeVisible()
  await expectAccessible(page)
  await expectWithinScreen(page)
})

test("keeps the search pages within a phone screen", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await openSearch(page)
  await expectWithinScreen(page)
  const header = page.getByRole("banner")
  const nav = header.getByRole("navigation")
  const tools = header.getByRole("button", { name: /language/i })
  const navBox = await nav.boundingBox()
  const toolsBox = await tools.boundingBox()
  expect((navBox?.x ?? 0) + (navBox?.width ?? 0)).toBeLessThanOrEqual(toolsBox?.x ?? 0)
})
