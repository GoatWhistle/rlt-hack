import AxeBuilder from "@axe-core/playwright"
import { expect, type Page, test } from "@playwright/test"
import { installApiFixture } from "./api-fixture"
import { chooseLanguage } from "./language"
import { installSearchFixture, openArchivedSearch } from "./search-fixture"

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
  if ((page.viewportSize()?.width ?? 0) < 1200) await views.getByRole("radio", { name }).check()
}

async function openSearch(page: Page) {
  await page.emulateMedia({ reducedMotion: "reduce" })
  await page.goto("/search")
  await chooseLanguage(page, /^english$/i)
  await expect(page.getByRole("heading", { level: 1, name: /find suppliers/i })).toBeVisible()
}

test("keeps an archived catalog result at its address", async ({ page }) => {
  await openSearch(page)
  await expectAccessible(page)
  await openArchivedSearch(page, QUERY)
  await expect(page).toHaveURL(/\/search\/[\w-]+$/)
  await expect(
    page.getByRole("textbox", { name: /describe what you need|опишите, что нужно/i }),
  ).toHaveValue(QUERY)

  await showView(page, /^candidates$/i)
  const candidates = page.getByRole("region", { name: /^candidates/i })
  await expect(candidates.getByRole("button", { pressed: true })).toBeVisible()
  await candidates.getByRole("button", { name: /Зерновой Двор/ }).click()
  const grounds = page.getByRole("article", { name: /Зерновой Двор/ })
  await expect(grounds).toBeVisible()
  await expect(grounds.getByText(/can.t be identified for sure/i)).toBeVisible()
  await expect(grounds.getByRole("heading", { name: /match by item/i })).toBeVisible()
  await expectAccessible(page)
  await expectWithinScreen(page)

  const address = page.url()
  await chooseLanguage(page, /^русский$/i)
  await expect(
    page.getByRole("article").getByRole("heading", { name: /Совпадение по позициям/ }),
  ).toBeVisible()
  await page.reload()
  expect(page.url()).toBe(address)
  await expect(
    page.getByRole("textbox", { name: /describe what you need|опишите, что нужно/i }),
  ).toHaveValue(QUERY)
  await showView(page, /^основания$/i)
  await expect(page.getByRole("article", { name: /Зерновой Двор/ })).toBeVisible()
  await expect(page.getByRole("link", { name: /^поиск$/i })).toHaveAttribute(
    "aria-current",
    "page",
  )
})

test("opens a company profile and returns to a recent search", async ({ page }) => {
  await openSearch(page)
  await openArchivedSearch(page, "Office paper A4 80 gsm, 300 reams")
  await expect(page).toHaveURL(/\/search\/[\w-]+$/)
  await expect(page.getByRole("note", { name: /may be incomplete/i })).toBeVisible()
  await page.getByRole("button", { name: /company profile/i }).click()
  const profile = page.getByRole("dialog", { name: /Северный Провиант/ })
  await expect(profile.getByRole("heading", { name: /for your request/i })).toBeVisible()
  await expect(profile.getByRole("article", { name: /Крупа гречневая ядрица/ })).toBeVisible()
  await expectAccessible(page)
  await page.keyboard.press("Escape")

  await page.getByRole("link", { name: /^search$/i }).click()
  const recent = page.getByRole("region", { name: /recent searches/i })
  await recent.getByRole("link", { name: /office paper/i }).click()
  await expect(page).toHaveURL(/\/search\/[\w-]+$/)
  await expectWithinScreen(page)
})

test("chooses a candidate and downloads the choice", async ({ page }) => {
  await openSearch(page)
  await openArchivedSearch(page, QUERY)
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
  await expect(
    page.getByRole("textbox", { name: /describe what you need|опишите, что нужно/i }),
  ).toHaveValue(QUERY)
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
  expect((await download).suggestedFilename()).toMatch(
    /^lotive-buckwheat-groats-500-\d{4}-\d{2}-\d{2}\.csv$/,
  )
  await expect(page.getByRole("listitem").filter({ hasText: /file downloaded/i })).toBeVisible()
})

test("shows the offers that cover the items and compares their prices", async ({ page }) => {
  await openSearch(page)
  await openArchivedSearch(page, `${QUERY}; many items`)
  await expect(page).toHaveURL(/\/search\/[\w-]+$/)
  await expect(page.getByRole("note", { name: /may be incomplete/i })).toContainText(
    /only the first ones were used/i,
  )
  await showView(page, /^evidence$/i)
  const grounds = page.getByRole("article", { name: /Северный Провиант/ })
  const offers = grounds.getByRole("list", { name: /offers covering the items/i })
  await expect(offers.getByRole("article")).toHaveCount(2)
  const offer = offers.getByRole("article", { name: /Крупа гречневая ядрица/ })
  await expect(offer.getByText(/84\.50 per кг/)).toBeVisible()
  await expect(offer.getByText(/Item “Крупа гречневая ядрица”/)).toBeVisible()
  await expect(offer.getByRole("link", { name: /new tab/i }).first()).toHaveAttribute(
    "target",
    "_blank",
  )
  await expectAccessible(page)
  await expectWithinScreen(page)

  await grounds.getByRole("button", { name: /choose candidate/i }).click()
  await showView(page, /^candidates$/i)
  await page
    .getByRole("region", { name: /^candidates/i })
    .getByRole("button", { name: /Зерновой Двор/ })
    .click()
  await showView(page, /^evidence$/i)
  const other = page.getByRole("article", { name: /Зерновой Двор/ })
  await expect(other.getByText(/no offer: the system infers/i)).toBeVisible()
  await other.getByRole("button", { name: /choose candidate/i }).click()
  await page.getByRole("button", { name: /compare chosen: 2/i }).click()
  const table = page.getByRole("dialog", { name: /compare/i }).getByRole("table")
  await expect(table.getByRole("row", { name: /^Крупа гречневая ядрица/ })).toContainText(
    /84\.50 per кг\s*In stock/,
  )
  await expectAccessible(page)
})

test("keeps an archived result without offers readable", async ({ page }) => {
  await openSearch(page)
  await openArchivedSearch(page, `${QUERY}; archived`)
  await showView(page, /^evidence$/i)
  const grounds = page.getByRole("article", { name: /Северный Провиант/ })
  await expect(grounds.getByRole("heading", { name: /match by item/i })).toBeVisible()
  await expect(grounds.getByRole("list", { name: /offers covering the items/i })).toHaveCount(0)
  await expect(grounds.getByText(/^in a price list$/i)).toBeVisible()
})

test("explains an empty archived result", async ({ page }) => {
  await openSearch(page)
  await openArchivedSearch(page, "Tractor tyres 4 pcs")
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
