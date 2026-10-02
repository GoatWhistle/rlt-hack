import { screen, within } from "@testing-library/react"
import { en } from "@tests/support/dictionaries"
import { renderWithProviders } from "@tests/support/render"
import { describe, expect, it } from "vitest"
import type { OfferView } from "@/entities/evidence/model"
import { ProfileOffers } from "@/entities/supplier/ui/profile-offers"

function offer(id: string, name: string, price?: number): OfferView {
  return { id, name, availability: "available", ...(price ? { price, currency: "RUB" } : {}) }
}

describe("the offers in a company profile", () => {
  it("puts the offers behind the request first and prefers their current state", () => {
    renderWithProviders(
      <ProfileOffers
        offers={[offer("o1", "Buckwheat now", 90), offer("o2", "Rice"), offer("o3", "Salt")]}
        matched={[
          {
            key: "i1",
            offer: offer("o1", "Buckwheat then", 80),
            link: { itemName: "Buckwheat", basis: "stock" },
          },
          {
            key: "i9",
            offer: offer("o9", "Gone offer"),
            link: { itemName: "Oil", basis: "catalog" },
          },
        ]}
      />,
    )
    const matched = screen.getByRole("list", { name: en("forQuery", "supplier") })
    expect(within(matched).getByText("Buckwheat now")).toBeVisible()
    expect(within(matched).getByText("Gone offer")).toBeVisible()
    expect(within(matched).getByText("Item “Buckwheat”")).toBeVisible()
    const others = screen.getByRole("list", { name: en("otherOffers", "supplier") })
    expect(within(others).getAllByRole("article")).toHaveLength(2)
    expect(within(others).queryByText("Buckwheat now")).toBeNull()
  })

  it("lists current offers when nothing was matched", () => {
    renderWithProviders(<ProfileOffers offers={[offer("o2", "Rice")]} matched={[]} />)
    expect(screen.getByRole("heading", { name: en("offers", "supplier") })).toBeVisible()
    expect(screen.queryByRole("heading", { name: en("forQuery", "supplier") })).toBeNull()
  })

  it("explains an empty assortment", () => {
    renderWithProviders(<ProfileOffers offers={[]} matched={[]} />)
    expect(screen.getByText(en("offer.empty", "evidence"))).toBeVisible()
    expect(screen.getByText(en("offer.emptyHint", "evidence"))).toBeVisible()
  })
})
