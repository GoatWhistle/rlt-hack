import { screen, within } from "@testing-library/react"
import { en } from "@tests/support/dictionaries"
import { renderWithProviders } from "@tests/support/render"
import { describe, expect, it } from "vitest"
import type { OfferView } from "@/entities/evidence/model"
import { OfferCard } from "@/entities/evidence/ui/offer-card"
import {
  OfferEmpty,
  type OfferEntry,
  OfferGrid,
  OfferGridSkeleton,
} from "@/entities/evidence/ui/offer-grid"

const DAY = 86_400_000

function daysAgo(days: number): string {
  return new Date(Date.now() - days * DAY).toISOString()
}

const FULL: OfferView = {
  id: "o1",
  name: "Buckwheat, 50 kg bag",
  price: 84.5,
  currency: "RUB",
  unit: "kg",
  availability: "available",
  brand: "Uvelka",
  article: "4607",
  okpd2: "10.61.32.110",
  attributes: [{ name: "Pack", value: "50 kg" }],
  seller: "verified",
  source: {
    kind: "price",
    title: "Company price list",
    url: "https://north.example.org/price",
    checkedAt: daysAgo(2),
  },
}

function card(offer: OfferView = FULL, link?: Parameters<typeof OfferCard>[0]["link"]) {
  renderWithProviders(<OfferCard offer={offer} link={link} />)
  return screen.getByRole("article", { name: new RegExp(`^${offer.name}`) })
}

describe("an offer card", () => {
  it("shows the product, its price, stock, codes, source and the item it covers", () => {
    const article = card(FULL, { itemName: "Buckwheat", basis: "stock" })
    const name = within(article).getByRole("link", { name: /^Buckwheat, 50 kg bag/ })
    expect(name).toHaveTextContent(en("newTab", "evidence"))
    expect(name).toHaveAttribute("href", "https://north.example.org/price")
    expect(name).toHaveAttribute("target", "_blank")
    expect(name).toHaveAttribute("rel", "noopener noreferrer")
    expect(within(article).getByText("RUB 84.50 per kg")).toBeVisible()
    expect(
      within(article).getByText(en("offer.availability.available", "evidence")),
    ).toBeVisible()
    expect(within(article).getByText("Uvelka")).toBeVisible()
    expect(within(article).getByText("SKU 4607")).toBeVisible()
    expect(within(article).getByText("OKPD2 10.61.32.110")).toBeVisible()
    expect(within(article).getByText("Pack: 50 kg")).toBeVisible()
    expect(within(article).getByText("Item “Buckwheat”")).toBeVisible()
    expect(within(article).getByText(en("basis.stock", "evidence"))).toBeVisible()
    expect(within(article).getByText(/^checked /)).toBeVisible()
    expect(within(article).queryByRole("img")).toBeNull()
    expect(within(article).queryByText(en("offer.seller.unverified", "evidence"))).toBeNull()
  })

  it("says when the price is missing and keeps the rest", () => {
    const article = card({ ...FULL, price: undefined, availability: "on_order" })
    expect(within(article).getByText(en("offer.noPrice", "evidence"))).toBeVisible()
    expect(
      within(article).getByText(en("offer.availability.on_order", "evidence")),
    ).toBeVisible()
  })

  it("marks an old check and an unconfirmed seller", () => {
    const source = FULL.source && { ...FULL.source, checkedAt: daysAgo(45) }
    const article = card({ ...FULL, seller: "unverified", source })
    expect(within(article).getByText(/may be outdated/)).toBeVisible()
    expect(within(article).getByText(en("offer.seller.unverified", "evidence"))).toBeVisible()
  })

  it("shows the image only when the source gives one", () => {
    const article = card({ ...FULL, imageUrl: "https://img.example.org/a.webp" })
    const image = article.querySelector("img")
    expect(image).toHaveAttribute("src", "https://img.example.org/a.webp")
    expect(image).toHaveAttribute("alt", "")
    expect(image).toHaveAttribute("loading", "lazy")
  })

  it("reads a bare catalog entry without inventing price or stock", () => {
    const article = card({ id: "c1", name: "A4 paper" })
    expect(within(article).queryByRole("link")).toBeNull()
    expect(within(article).queryByText(en("offer.noPrice", "evidence"))).toBeNull()
    expect(within(article).getByText(en("noSource", "evidence"))).toBeVisible()
  })

  it("prints a currency it cannot format as a code", () => {
    const article = card({
      ...FULL,
      currency: "руб.",
      unit: undefined,
      availability: "unknown",
    })
    expect(within(article).getByText("84.5 руб.")).toBeVisible()
    expect(
      within(article).getByText(en("offer.availability.unknown", "evidence")),
    ).toBeVisible()
  })

  it("prints a bare number without a currency", () => {
    const article = card({ ...FULL, currency: undefined, unit: undefined })
    expect(within(article).getByText("84.5")).toBeVisible()
  })
})

const entries: OfferEntry[] = Array.from({ length: 5 }, (_, index) => ({
  offer: { ...FULL, id: `o${index}`, name: `Offer ${index}` },
}))

describe("an offer grid", () => {
  it("folds offers beyond the limit and unfolds them on request", async () => {
    const { user } = renderWithProviders(
      <OfferGrid entries={entries} label="Offers" limit={2} ribbon />,
    )
    const list = screen.getByRole("list", { name: "Offers" })
    expect(within(list).getAllByRole("listitem")).toHaveLength(2)
    await user.click(screen.getByRole("button", { name: "Show all 5" }))
    expect(within(list).getAllByRole("listitem")).toHaveLength(5)
    await user.click(screen.getByRole("button", { name: en("action.showLess") }))
    expect(within(list).getAllByRole("listitem")).toHaveLength(2)
  })

  it("shows everything without a limit", () => {
    renderWithProviders(<OfferGrid entries={entries} label="Offers" />)
    expect(screen.getAllByRole("listitem")).toHaveLength(5)
    expect(screen.queryByRole("button")).toBeNull()
  })

  it("has a skeleton of the same layout and an empty state", () => {
    const { container } = renderWithProviders(
      <>
        <OfferGridSkeleton count={3} ribbon />
        <OfferEmpty title="No offers" hint="Ask the company" />
        <OfferEmpty title="Nothing" />
      </>,
    )
    expect(container.querySelectorAll('[class*="bone"]')).toHaveLength(12)
    expect(screen.getByText("No offers")).toBeVisible()
    expect(screen.getByText("Ask the company")).toBeVisible()
  })
})
