import { expect, test } from "@playwright/test"
import { chooseLanguage } from "../language"

const SAMPLE = "public/notices-sample.csv"

test("a real csv goes through the api into saved searches and two result files", async ({
  page,
}) => {
  await page.emulateMedia({ reducedMotion: "reduce" })
  await page.goto("/uploads")
  await chooseLanguage(page, /^english$/i)
  await page.getByLabel(/choose file/i).setInputFiles(SAMPLE)
  const dialog = page.getByRole("dialog", { name: /new upload/i })
  await dialog.getByRole("button", { name: /process 5 purchases/i }).click()
  await expect(page).toHaveURL(/\/uploads\/[\w-]+$/)
  await expect(page.getByText(/processing finished/i)).toBeVisible({ timeout: 90_000 })
  const uploadId = page.url().split("/").pop() ?? ""
  const detail = await page.request.get(`/api/uploads/${uploadId}`)
  expect(detail.status()).toBe(200)
  const body = await detail.json()
  expect(body.counts.failed).toBe(0)
  expect(body.processed).toBe(body.total)

  await page.getByRole("table").getByRole("link").first().click()
  await expect(page).toHaveURL(/\/lots\//)
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible()
  const lotId = decodeURIComponent(new URL(page.url()).pathname.split("/").pop() ?? "")
  const lot = await (await page.request.get(`/api/uploads/${uploadId}/lots/${lotId}`)).json()
  expect(lot.search.searchId).toBe(lot.lot.searchId)
  const manual = await (
    await page.request.post("/api/searches", { data: { text: lot.search.query.text } })
  ).json()
  expect(manual.candidates.map((item: { id: string }) => item.id)).toEqual(
    lot.search.candidates.map((item: { id: string }) => item.id),
  )

  await page.getByRole("button", { name: /download results/i }).click()
  const exporting = page.getByRole("dialog", { name: /download/i })
  const names: string[] = []
  page.on("download", (file) => names.push(file.suggestedFilename()))
  await exporting.getByRole("button", { name: /download 2 csv/i }).click()
  await expect.poll(() => names.length).toBe(2)
  expect(names.sort()).toEqual(["notices-sample-products.csv", "notices-sample-suppliers.csv"])

  const foreign = await page.request.get(`/api/uploads/${uploadId}`, {
    headers: { cookie: "rlt_session=00000000000000000000000000000000" },
  })
  expect(foreign.status()).toBe(404)
})
