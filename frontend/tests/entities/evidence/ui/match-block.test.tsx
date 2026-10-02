import { screen, within } from "@testing-library/react"
import { en } from "@tests/support/dictionaries"
import { renderWithProviders } from "@tests/support/render"
import { describe, expect, it } from "vitest"
import type { OfferView } from "@/entities/evidence/model"
import {
  MatchBlock,
  OFFER_LIMIT,
  offerEntries,
} from "@/entities/evidence/ui/candidate-panel/blocks"
import { type CandidateView, type ItemView, rowsOf } from "@/entities/evidence/view"

const SOURCE = {
  kind: "price",
  title: "Price list",
  url: "https://north.example.org/price",
  checkedAt: "2026-09-29T08:00:00Z",
} as const

function offer(id: string, name: string): OfferView {
  return {
    id,
    name,
    price: 10,
    currency: "RUB",
    unit: "kg",
    availability: "available",
    source: SOURCE,
  }
}

const ITEMS: ItemView[] = [
  { id: "i1", name: "Buckwheat" },
  { id: "i2", name: "Rice" },
  { id: "i3", name: "Salt" },
  { id: "i4", name: "Sugar" },
  { id: "i5", name: "Oil" },
]

const CANDIDATE: CandidateView = {
  id: "c1",
  rank: 1,
  name: "North",
  inn: "",
  role: "supplier",
  status: "recommended",
  checkReasons: [],
  highlights: [],
  similarPurchases: 0,
  wins: 0,
  purchases: [],
  matches: [
    {
      itemId: "i2",
      basis: "catalog",
      offerId: "o2",
      source: SOURCE,
      offer: offer("o2", "Rice 1 kg"),
    },
    {
      itemId: "i1",
      basis: "stock",
      offerId: "o1",
      source: SOURCE,
      offer: offer("o1", "Buckwheat 50 kg"),
    },
    { itemId: "i3", basis: "inferred" },
    { itemId: "i4", basis: "stock", offerId: "o4", source: SOURCE },
  ],
}

describe("the match block", () => {
  it("shows offers as cards and keeps the rest as rows", () => {
    renderWithProviders(<MatchBlock candidate={CANDIDATE} items={ITEMS} />)
    const cards = screen.getByRole("list", { name: en("panel.offersLabel", "candidate") })
    const names = within(cards)
      .getAllByRole("article")
      .map(
        (card) => card.getAttribute("aria-labelledby") && card.querySelector("p")?.textContent,
      )
    expect(names[0]).toMatch(/^Buckwheat 50 kg/)
    expect(names[1]).toMatch(/^Rice 1 kg/)
    expect(within(cards).getByText("Item “Rice”")).toBeVisible()
    expect(within(cards).getByText(en("basis.catalog", "evidence"))).toBeVisible()
    expect(screen.getByText(en("offer.inferred", "evidence"))).toBeVisible()
    expect(screen.getByText(en("notFound", "evidence"))).toBeVisible()
    expect(screen.getByText("Sugar")).toBeVisible()
  })

  it("collects one entry per item that an offer covers", () => {
    const entries = offerEntries(rowsOf(CANDIDATE, ITEMS))
    expect(entries.map((entry) => [entry.key, entry.offer.id, entry.link?.basis])).toEqual([
      ["i1", "o1", "stock"],
      ["i2", "o2", "catalog"],
    ])
    expect(OFFER_LIMIT).toBe(4)
  })
})
