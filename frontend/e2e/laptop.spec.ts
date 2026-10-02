import { expect, type Locator, test } from "@playwright/test"
import { installApiFixture } from "./api-fixture"
import { chooseLanguage } from "./language"
import { installSearchFixture, openArchivedSearch } from "./search-fixture"

const LAPTOP = { width: 1366, height: 768 }
const QUERY = "Buckwheat groats 500 kg; polished rice 200 kg"

test.skip(({ isMobile }) => isMobile, "laptop screen only")

test.beforeEach(async ({ page }) => {
  await installApiFixture(page)
  await installSearchFixture(page)
  await page.setViewportSize(LAPTOP)
  await page.emulateMedia({ reducedMotion: "reduce" })
})

async function expectReachable(target: Locator) {
  const box = await target.boundingBox()
  expect(box).not.toBeNull()
  if (!box) return
  expect(box.y).toBeGreaterThanOrEqual(0)
  expect(box.y + box.height).toBeLessThanOrEqual(LAPTOP.height)
  const hit = await target.evaluate((element) => {
    const rect = element.getBoundingClientRect()
    const found = document.elementFromPoint(rect.x + rect.width / 2, rect.y + rect.height / 2)
    return Boolean(found && element.contains(found))
  })
  expect(hit).toBe(true)
}

test("puts the comparison in the header and keeps its dialog on screen", async ({ page }) => {
  await page.goto("/search")
  await chooseLanguage(page, /^english$/i)
  await openArchivedSearch(page, QUERY)
  await expect(page).toHaveURL(/\/search\/[\w-]+$/)

  const header = page.getByRole("main").locator("header")
  const grounds = page.getByRole("article", { name: /Северный Провиант/ })
  await grounds.getByRole("button", { name: /choose candidate/i }).click()
  await page.evaluate(() => window.scrollTo(0, 0))
  const compare = header.getByRole("button", { name: /compare chosen: 1/i })
  await expect(compare).toHaveAttribute("aria-disabled", "true")
  await expect(header.getByText(/pick one more to compare/i)).toBeVisible()
  await page
    .getByRole("region", { name: /^candidates/i })
    .getByRole("button", { name: /Зерновой Двор/ })
    .click()
  const other = page.getByRole("article", { name: /Зерновой Двор/ })
  await other.getByRole("button", { name: /choose candidate/i }).click()
  await expect(page.getByRole("region", { name: /chosen candidates/i })).toHaveCount(0)
  await page.evaluate(() => window.scrollTo(0, 0))
  await expectReachable(header.getByRole("button", { name: /compare chosen: 2/i }))
  await page.evaluate(() => window.scrollTo(0, document.documentElement.scrollHeight))
  const docked = other.getByRole("button", { name: /compare chosen: 2/i })
  await expectReachable(docked)
  await docked.click()
  const dialog = page.getByRole("dialog", { name: /compare/i })
  await expect(dialog.getByRole("table")).toBeVisible()
  await expectReachable(dialog.getByRole("button", { name: /^close$/i }))
  await page.keyboard.press("Escape")
  await expect(dialog).toBeHidden()

  await page.evaluate(() => window.scrollTo(0, 0))
  await page.getByRole("button", { name: /^clear$/i }).click()
  await expect(page.getByRole("button", { name: /compare chosen/i })).toHaveCount(0)
  await page.locator("body").click({ position: { x: 5, y: 700 } })
  await page.keyboard.press("/")
  await expect(page.getByRole("textbox", { name: /describe what you need/i })).toBeFocused()
})
