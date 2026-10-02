import { expect, type Page, test } from "@playwright/test"
import { installApiFixture } from "./api-fixture"
import { installSearchFixture } from "./search-fixture"

const SCREENS = [
  { width: 360, height: 740 },
  { width: 768, height: 1024 },
  { width: 1280, height: 800 },
  { width: 1920, height: 1080 },
  { width: 2560, height: 1440 },
] as const
const WIDE = 1920
const TOLERANCE = 2
const QUERY = "Buckwheat groats 500 kg; polished rice 200 kg"

type Frame = {
  readonly scroll: number
  readonly client: number
  readonly left: number
  readonly right: number
  readonly brand: number
}

test.skip(({ isMobile }) => isMobile, "the matrix sets its own screens")

test.beforeEach(async ({ page }) => {
  await installApiFixture(page)
  await installSearchFixture(page)
  await page.emulateMedia({ reducedMotion: "reduce" })
  await page.addInitScript(() => localStorage.setItem("rlt-locale", "en"))
})

function frame(page: Page): Promise<Frame> {
  return page.evaluate(
    () =>
      new Promise<Frame>((resolve) =>
        requestAnimationFrame(() =>
          requestAnimationFrame(() => {
            const root = document.documentElement
            const main = document.querySelector("main")
            const brand = document.querySelector("header a")
            if (!main || !brand) throw new Error("the shell is not rendered")
            const box = main.getBoundingClientRect()
            const style = getComputedStyle(main)
            const left = box.left + Number.parseFloat(style.paddingLeft)
            const right = box.right - Number.parseFloat(style.paddingRight)
            resolve({
              scroll: root.scrollWidth,
              client: root.clientWidth,
              left,
              right: root.clientWidth - right,
              brand: brand.getBoundingClientRect().left,
            })
          }),
        ),
      ),
  )
}

async function expectAdaptive(page: Page) {
  for (const screen of SCREENS) {
    await page.setViewportSize(screen)
    const measured = await frame(page)
    expect(measured.scroll, `overflow at ${screen.width}`).toBeLessThanOrEqual(measured.client)
    expect(Math.abs(measured.left - measured.right)).toBeLessThanOrEqual(TOLERANCE)
    expect(Math.abs(measured.brand - measured.left)).toBeLessThanOrEqual(TOLERANCE)
    if (screen.width > WIDE) {
      expect(measured.left, `content hugs the edge at ${screen.width}`).toBeGreaterThan(
        (screen.width - WIDE) / 4,
      )
    }
  }
}

test("fits the search pages to every screen", async ({ page }) => {
  await page.goto("/search")
  await expect(page.getByRole("heading", { level: 1, name: /find suppliers/i })).toBeVisible()
  await expectAdaptive(page)
  await page.setViewportSize({ width: 1440, height: 900 })
  await page.getByRole("textbox", { name: /describe what you need/i }).fill(QUERY)
  await page.getByRole("button", { name: /^find$/i }).click()
  await expect(page).toHaveURL(/\/search\/[\w-]+$/)
  await expect(page.getByRole("article").first()).toBeVisible()
  await expectAdaptive(page)
})

test("fits the uploads, purchases and missing pages to every screen", async ({ page }) => {
  for (const [path, ready] of [
    ["/uploads", page.getByRole("heading", { level: 1 })],
    ["/uploads/test-upload", page.getByRole("table")],
    ["/uploads/test-upload/lots/test_paper", page.getByRole("article").first()],
    ["/nowhere", page.getByRole("heading", { level: 1, name: /not found/i })],
  ] as const) {
    await page.setViewportSize({ width: 1440, height: 900 })
    await page.goto(path)
    await expect(ready).toBeVisible()
    await expectAdaptive(page)
  }
})
