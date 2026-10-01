import AxeBuilder from "@axe-core/playwright"
import { expect, type Page, test } from "@playwright/test"

const WCAG_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"]

async function openResults(page: Page) {
  await page.emulateMedia({ reducedMotion: "reduce" })
  await page.goto("/")
  await page.getByRole("radio", { name: /^(english)$/i }).check()
  await page.getByLabel(/choose file/i).setInputFiles({
    name: "lot.xlsx",
    mimeType: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    buffer: Buffer.from("lot"),
  })
  await page.getByRole("button", { name: /find suppliers/i }).click()
  await expect(page).toHaveURL(/\/results$/)
}

test("turns an uploaded file into an explained list of companies", async ({ page }) => {
  await openResults(page)
  const candidates = page.getByRole("region", { name: /candidates/i }).getByRole("button")
  await candidates.last().click()
  await expect(page.getByRole("button", { pressed: true })).toHaveCount(1)
  await expect(page.getByRole("article").getByRole("heading", { level: 3 })).toHaveCount(4)
  const { violations } = await new AxeBuilder({ page }).withTags(WCAG_TAGS).analyze()
  const blocking = violations.filter(
    (violation) => violation.impact === "serious" || violation.impact === "critical",
  )
  expect(blocking.map((violation) => violation.id)).toEqual([])
})

test("shows the choice, its reason, a source and the main caveat on a laptop screen", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1440, height: 900 })
  await openResults(page)
  const grounds = page.getByRole("article")
  await expect(page.getByRole("button", { pressed: true })).toBeInViewport()
  await expect(grounds.getByRole("heading", { name: /why we recommend it/i })).toBeInViewport()
  await expect(grounds.getByText(/key thing to clarify/i)).toBeInViewport()
  await expect(grounds.getByRole("link").first()).toBeInViewport()
})

test("moves through companies with the keyboard", async ({ page }) => {
  await openResults(page)
  const second = page
    .getByRole("region", { name: /candidates/i })
    .getByRole("button")
    .nth(1)
  const name = (await second.textContent()) ?? ""
  await second.focus()
  await page.keyboard.press("Enter")
  await expect(page.getByRole("button", { pressed: true })).toBeFocused()
  await expect(page.getByRole("article")).toContainText(name.slice(1, 12))
})
