import { describe, expect, it } from "vitest"
import { catalogOfferView } from "@/pages/lot/evidence-panel/history-block/catalog"

describe("a published catalog entry", () => {
  it("becomes an offer with its page as the source", () => {
    expect(
      catalogOfferView({
        name: "A4 paper",
        url: "https://www.paper.example.org/a4",
        checkedAt: "2026-09-28",
      }),
    ).toEqual({
      id: "https://www.paper.example.org/a4",
      name: "A4 paper",
      source: {
        kind: "catalog",
        title: "paper.example.org",
        url: "https://www.paper.example.org/a4",
        checkedAt: "2026-09-28",
      },
    })
  })

  it("keeps an unreadable address and drops an unreadable date", () => {
    const offer = catalogOfferView({ name: "Pens", url: "pens", checkedAt: "recently" })
    expect(offer.source).toEqual({ kind: "catalog", title: "pens", url: "pens" })
  })
})
