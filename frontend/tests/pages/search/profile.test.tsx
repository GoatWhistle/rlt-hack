import { screen, within } from "@testing-library/react"
import { en } from "@tests/support/dictionaries"
import { renderSearch, stubSuppliers } from "@tests/support/search"
import { describe, expect, it, vi } from "vitest"
import { ApiError } from "@/shared/api/api-error"

describe("the company profile from a search", () => {
  it("opens the company profile with current offers", async () => {
    const { user } = renderSearch("/search/1f0c")
    await screen.findByRole("heading", { level: 1 })
    await user.click(screen.getByRole("button", { name: en("panel.profile", "candidate") }))
    const dialog = await screen.findByRole("dialog", { name: "ООО «Северный Провиант»" })
    expect(
      await within(dialog).findByText("Крупа гречневая ядрица 1 сорт, мешок 50 кг"),
    ).toBeVisible()
    expect(within(dialog).getByText("₽84.50 per кг")).toBeVisible()
    expect(
      within(dialog).getByRole("heading", { name: en("forQuery", "supplier") }),
    ).toBeTruthy()
    expect(within(dialog).getByText(en("identity.verified", "supplier"))).toBeVisible()
  })

  it("names a failed profile and gives the request number for support", async () => {
    const profile = vi
      .fn()
      .mockRejectedValue(
        new ApiError({ status: 404, code: "supplier_not_found", requestId: "req-7f3a" }),
      )
    const { user } = renderSearch("/search/1f0c", { suppliers: stubSuppliers({ profile }) })
    await screen.findByRole("heading", { level: 1 })
    await user.click(screen.getByRole("button", { name: en("panel.profile", "candidate") }))
    const dialog = await screen.findByRole("dialog", { name: "ООО «Северный Провиант»" })
    expect(
      await within(dialog).findByRole("heading", { name: en("error", "supplier") }),
    ).toBeVisible()
    expect(within(dialog).getByText("Code for support: req-7f3a")).toBeVisible()
  })
})
