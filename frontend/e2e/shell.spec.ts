import AxeBuilder from "@axe-core/playwright"
import { expect, test } from "@playwright/test"

const WCAG_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"]
const ROUTES = ["/", "/results", "/missing-page"]

test.describe("application shell", () => {
  for (const route of ROUTES) {
    test(`has no serious accessibility violations on ${route}`, async ({ page }) => {
      await page.emulateMedia({ reducedMotion: "reduce" })
      await page.goto(route)
      await expect(page.getByRole("heading", { level: 1 })).toBeVisible()
      const { violations } = await new AxeBuilder({ page }).withTags(WCAG_TAGS).analyze()
      const blocking = violations.filter(
        (violation) => violation.impact === "serious" || violation.impact === "critical",
      )
      expect(blocking.map((violation) => violation.id)).toEqual([])
    })
  }

  test("switches language and remembers it after a reload", async ({ page }) => {
    await page.goto("/")
    await page.getByRole("radio", { name: /^(english)$/i }).check()
    await expect(page.locator("html")).toHaveAttribute("lang", "en")
    await page.getByRole("radio", { name: /^(русский)$/i }).check()
    await page.reload()
    await expect(page.locator("html")).toHaveAttribute("lang", "ru")
  })

  test("reaches the main content from the skip link", async ({ page }) => {
    await page.goto("/")
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible()
    await page.keyboard.press("Tab")
    const skip = page.getByRole("link", { name: /(skip to content|перейти к содержимому)/i })
    await expect(skip).toBeFocused()
    await page.keyboard.press("Enter")
    await expect(page.locator("#main-content")).toBeFocused()
  })

  test("leads from an unknown address back home", async ({ page }) => {
    await page.goto("/missing-page")
    await page.getByRole("link", { name: /(go home|на главную)/i }).click()
    await expect(page).toHaveURL(/\/$/)
  })
})
