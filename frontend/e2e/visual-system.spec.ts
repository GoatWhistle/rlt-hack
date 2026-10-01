import { expect, test } from "@playwright/test"
import { installApiFixture } from "./api-fixture"

test.beforeEach(async ({ page }) => installApiFixture(page))

test("loads fonts from the application without external requests", async ({ page }) => {
  const external: string[] = []
  page.on("request", (request) => {
    const url = new URL(request.url())
    if (!["127.0.0.1", "localhost"].includes(url.hostname)) external.push(request.url())
  })
  await page.route(/fonts\.(googleapis|gstatic)\.com/, (route) => route.abort())
  await page.goto("/uploads")
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible()
  const loaded = await page.evaluate(async () => {
    await document.fonts.ready
    await Promise.all([
      document.fonts.load("400 16px Onest", "Аб"),
      document.fonts.load("600 16px Onest", "Ab"),
      document.fonts.load("400 16px 'IBM Plex Mono'", "12"),
    ])
    const families = [...document.fonts]
      .filter((face) => face.status === "loaded")
      .map((face) => face.family.replaceAll('"', ""))
    return [...new Set(families)].sort()
  })
  expect(loaded).toEqual(["IBM Plex Mono", "Onest"])
  expect(external).toEqual([])
})

test("shows a failed upload start inside the dialog", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" })
  await page.goto("/uploads")
  await page.route("**/api/uploads", (route) =>
    route.request().method() === "POST"
      ? route.fulfill({ status: 500, json: { code: "server" } })
      : route.fallback(),
  )
  await page.locator("input[type=file]").setInputFiles("public/notices-sample.csv")
  const dialog = page.getByRole("dialog")
  const start = dialog.getByRole("button", { name: /^(process|обработать)/i })
  await start.click()
  const alert = dialog.getByRole("alert")
  await expect(alert).toBeVisible()
  const inside = await alert.evaluate((element) => {
    const box = element.getBoundingClientRect()
    const hit = document.elementFromPoint(box.x + box.width / 2, box.y + box.height / 2)
    return Boolean(hit && element.closest("dialog")?.contains(hit))
  })
  expect(inside).toBe(true)
  await expect(start).toBeEnabled()
})
