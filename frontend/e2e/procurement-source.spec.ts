import AxeBuilder from "@axe-core/playwright"
import { expect, test } from "@playwright/test"
import { chooseLanguage } from "./language"

test("opens a readable procurement source with accessible facts", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" })
  await page.route("**/api/uploads/u1/lots/paper/evidence/1111111111/archive-1", (route) =>
    route.fulfill({
      json: {
        provenance: "procurement_archive",
        title: "Office paper procurement",
        lot_id: "archive-1",
        supplier_inn: "1111111111",
        customer_inn: "2222222222",
        category: "17.12",
        source_system: "Archive",
        product_names: ["A4 paper"],
        is_winner: true,
        publish_date: "2024-11-06",
      },
    }),
  )
  await page.goto("/uploads/u1/lots/paper/evidence/1111111111/archive-1")
  await chooseLanguage(page, /^english$/i)
  await expect(
    page.getByRole("heading", { level: 1, name: "Office paper procurement" }),
  ).toBeVisible()
  await expect(page.getByText("A4 paper")).toBeVisible()
  await expect(page.getByText("Winner", { exact: true })).toBeVisible()
  await expect(page.getByRole("link", { name: "Back to recommendation" })).toHaveAttribute(
    "href",
    "/uploads/u1/lots/paper",
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
