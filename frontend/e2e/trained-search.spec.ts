import AxeBuilder from "@axe-core/playwright"
import { expect, test } from "@playwright/test"
import { installApiFixture } from "./api-fixture"
import { chooseLanguage } from "./language"
import { installSearchFixture } from "./search-fixture"

test("submits the form through CSV and restores its saved recommendation", async ({ page }) => {
  await installApiFixture(page)
  await installSearchFixture(page)
  await page.goto("/search")
  await chooseLanguage(page, /^english$/i)
  const query = 'Drinking water "spring"; 200 bottles'
  await page.getByRole("textbox", { name: /describe what you need/i }).fill(query)
  const uploaded = page.waitForRequest(
    (request) => request.url().endsWith("/api/uploads") && request.method() === "POST",
  )
  await page.getByRole("button", { name: /^find$/i }).click()
  const request = await uploaded
  expect(request.postData()).toContain('Drinking water ""spring""; 200 bottles')
  await expect(page).toHaveURL(/\/uploads\/test-upload\/lots\/query$/)
  await expect(page.getByRole("heading", { level: 1, name: query })).toBeVisible()
  await expect(page.getByRole("article")).toBeVisible()
  const address = page.url()
  await page.reload()
  await expect(page).toHaveURL(address)
  await expect(page.getByRole("heading", { level: 1, name: query })).toBeVisible()
  const { violations } = await new AxeBuilder({ page }).analyze()
  expect(
    violations.filter((issue) => ["serious", "critical"].includes(issue.impact ?? "")),
  ).toEqual([])
})

test("sends notices and positions together", async ({ page }) => {
  await installApiFixture(page)
  await page.goto("/search")
  await chooseLanguage(page, /^english$/i)
  await page
    .locator("input[type=file]")
    .first()
    .setInputFiles({
      name: "notices.csv",
      mimeType: "text/csv",
      buffer: Buffer.from("lot_id;procedure_name\n1;Water"),
    })
  await page
    .locator("input[type=file]")
    .nth(1)
    .setInputFiles({
      name: "items.csv",
      mimeType: "text/csv",
      buffer: Buffer.from("lot_id;product_name;okpd2_code\n1;Drinking water;11.07"),
    })
  const sent = page.waitForRequest(
    (request) => request.url().endsWith("/api/uploads") && request.method() === "POST",
  )
  await page.getByRole("button", { name: /^find$/i }).click()
  const body = (await sent).postData()
  expect(body).toContain('name="file"; filename="notices.csv"')
  expect(body).toContain('name="items_file"; filename="items.csv"')
  expect(body).toContain("Drinking water;11.07")
  await expect(page).toHaveURL(/\/uploads\/test-upload(\/lots\/1)?$/)
})
