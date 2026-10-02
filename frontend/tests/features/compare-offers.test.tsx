import { screen, within } from "@testing-library/react"
import { en } from "@tests/support/dictionaries"
import { renderWithProviders } from "@tests/support/render"
import { describe, expect, it } from "vitest"
import type { MatchBasis, OfferView } from "@/entities/evidence/model"
import type { CandidateView, ItemView } from "@/entities/evidence/view"
import { CompareDialog } from "@/features/compare-candidates"
import { comparablePrices } from "@/features/compare-candidates/offer-criteria"

const ITEMS: ItemView[] = [
  { id: "i1", name: "Buckwheat" },
  { id: "i2", name: "Rice" },
  { id: "i3", name: "Salt" },
]

function priced(price: number, unit = "kg"): OfferView {
  return {
    id: `o${price}`,
    name: "Offer",
    price,
    currency: "RUB",
    unit,
    availability: "available",
  }
}

function candidate(
  id: string,
  matches: readonly [string, MatchBasis, OfferView?][],
): CandidateView {
  return {
    id,
    rank: 1,
    name: id,
    inn: "",
    role: "supplier",
    status: "recommended",
    checkReasons: [],
    highlights: [],
    similarPurchases: 0,
    wins: 0,
    purchases: [],
    matches: matches.map(([itemId, basis, offer]) =>
      offer ? { itemId, basis, offer } : { itemId, basis },
    ),
  }
}

const NORTH = candidate("North", [
  ["i1", "stock", priced(84.5)],
  ["i2", "catalog", priced(40, "pack")],
])
const SOUTH = candidate("South", [
  ["i1", "stock", priced(90)],
  ["i2", "stock", priced(35)],
])
const WEST = candidate("West", [["i1", "inferred"]])

describe("comparing offers", () => {
  it("adds a row per item with price and stock and marks the cheapest", () => {
    renderWithProviders(
      <CompareDialog open candidates={[NORTH, SOUTH, WEST]} items={ITEMS} onClose={() => {}} />,
    )
    const buckwheat = screen.getByRole("row", { name: /^Buckwheat/ })
    const cells = within(buckwheat).getAllByRole("cell")
    expect(cells[0]).toHaveTextContent("RUB 84.50 per kg · In stock")
    expect(cells[0]).toHaveTextContent(en("compare.best", "candidate"))
    expect(cells[1]).not.toHaveTextContent(en("compare.best", "candidate"))
    expect(cells[2]).toHaveTextContent(en("basis.inferred", "evidence"))
    const rice = screen.getByRole("row", { name: /^Rice/ })
    expect(within(rice).queryByText(en("compare.best", "candidate"))).toBeNull()
    expect(within(rice).getAllByRole("cell")[2]).toHaveTextContent(en("notFound", "evidence"))
    expect(screen.queryByRole("row", { name: /^Salt/ })).toBeNull()
  })

  it("compares prices only in the same currency and unit", () => {
    expect([...comparablePrices([NORTH, SOUTH], "i1")]).toEqual([
      ["North", 84.5],
      ["South", 90],
    ])
    expect(comparablePrices([NORTH, SOUTH], "i2").size).toBe(0)
    expect(comparablePrices([NORTH], "i1").size).toBe(0)
  })
})
