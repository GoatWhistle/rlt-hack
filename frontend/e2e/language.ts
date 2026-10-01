import { expect, type Page } from "@playwright/test"

export async function chooseLanguage(page: Page, name: RegExp): Promise<void> {
  await page.getByRole("button", { name: /^(language|язык): /i }).click()
  await page.getByRole("menuitemradio", { name }).click()
  await expect(page.getByRole("menu")).toHaveCount(0)
}
