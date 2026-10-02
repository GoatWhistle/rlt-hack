import { readFileSync } from "node:fs"
import AxeBuilder from "@axe-core/playwright"
import { expect, test } from "@playwright/test"
import { chooseLanguage } from "./language"

const source = JSON.parse(readFileSync("../contracts/supplier/purchase.example.json", "utf8"))

test("opens a readable procurement source with accessible facts", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" })
  await page.route("**/api/suppliers/c1/purchases/4012345", (route) =>
    route.fulfill({ json: source }),
  )
  await page.goto(`/suppliers/c1/purchases/4012345?back=${encodeURIComponent("/search/s1")}`)
  await chooseLanguage(page, /^english$/i)
  await expect(page.getByRole("heading", { level: 1, name: source.title })).toBeVisible()
  await expect(page.getByText("Рис шлифованный")).toBeVisible()
  await expect(page.getByText("Winner", { exact: true })).toBeVisible()
  await expect(page.getByRole("link", { name: "Back to recommendation" })).toHaveAttribute(
    "href",
    "/search/s1",
  )
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(
    true,
  )
  const { violations } = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"])
    .analyze()
  expect(
    violations.filter((item) => item.impact === "serious" || item.impact === "critical"),
  ).toEqual([])
})
