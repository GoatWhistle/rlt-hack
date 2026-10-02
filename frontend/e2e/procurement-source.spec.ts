import AxeBuilder from "@axe-core/playwright"
import { expect, test } from "@playwright/test"
import { recommendationFixture } from "../tests/entities/recommendation/fixture"
import { installApiFixture } from "./api-fixture"
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

test("shows historical item matches with a dated archive source", async ({ page }) => {
  await installApiFixture(page)
  const company = recommendationFixture.companies[0]
  const product = recommendationFixture.products[0]
  if (!company || !product) throw new Error("missing synthetic fixture")
  await page.route("**/api/uploads/test-upload/lots/test_paper", (route) =>
    route.fulfill({
      json: {
        lot: {
          id: "test_paper",
          title: "Paper procurement",
          status: "ready",
          products: 1,
          candidates: 1,
        },
        upload: {
          id: "test-upload",
          fileName: "two.csv",
          createdAt: "2026-10-02",
          total: 1,
          processed: 1,
          counts: { ready: 1, needsCheck: 0, noCandidates: 0, failed: 0 },
          rejected: 0,
        },
        recommendation: {
          ...recommendationFixture,
          products: [product],
          companies: [
            {
              ...company,
              matches: [
                {
                  productId: product.id,
                  basis: "historical",
                  source: {
                    kind: "purchase",
                    title: "Verified archived procurement",
                    url: "/uploads/test-upload/lots/test_paper/evidence/7800000011/archive-1",
                    checkedAt: "2025-02-01",
                  },
                },
              ],
            },
          ],
        },
      },
    }),
  )
  await page.goto("/uploads/test-upload/lots/test_paper")
  await chooseLanguage(page, /^english$/i)
  await expect(
    page.getByText("Item in a procurement with this company participating").first(),
  ).toBeVisible()
  await expect(
    page.getByRole("link", { name: /Verified archived procurement/ }).first(),
  ).toBeVisible()
  await expect(page.getByText(/procurement date/).first()).toBeVisible()
})
