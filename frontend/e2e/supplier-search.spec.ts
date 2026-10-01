import AxeBuilder from "@axe-core/playwright"
import { expect, test } from "@playwright/test"

const WCAG_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"]

test("turns an uploaded file into an explained list of companies", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" })
  await page.goto("/")
  await page.getByLabel(/(choose file|выбрать файл)/i).setInputFiles({
    name: "lot.xlsx",
    mimeType: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    buffer: Buffer.from("lot"),
  })
  await page.getByRole("button", { name: /(find suppliers|подобрать поставщиков)/i }).click()
  await expect(page).toHaveURL(/\/results$/)
  const companies = page.getByRole("button", { pressed: false })
  await companies.first().click()
  await expect(page.getByRole("button", { pressed: true })).toHaveCount(1)
  await expect(page.getByRole("heading", { level: 3 })).toHaveCount(3)
  const { violations } = await new AxeBuilder({ page }).withTags(WCAG_TAGS).analyze()
  const blocking = violations.filter(
    (violation) => violation.impact === "serious" || violation.impact === "critical",
  )
  expect(blocking.map((violation) => violation.id)).toEqual([])
})
