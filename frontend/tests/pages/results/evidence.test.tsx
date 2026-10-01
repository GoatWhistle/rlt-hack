import { screen, within } from "@testing-library/react"
import { en } from "@tests/support/dictionaries"
import { describe, expect, it, vi } from "vitest"
import { STACKED_LAYOUT } from "@/pages/results"
import { LONG_NAME, recommendationFixture } from "../../entities/recommendation/fixture"
import { openResults } from "./open-results"

function panel(name: string | RegExp) {
  return screen.getByRole("article", { name })
}

describe("the grounds panel", () => {
  it("opens with the short reason, the main caveat and the tax id", async () => {
    await openResults(recommendationFixture)
    const grounds = panel("North Foods")
    expect(within(grounds).getByText("Supplier · Tax ID 7800000011")).toBeInTheDocument()
    expect(
      within(grounds).getByRole("heading", {
        level: 3,
        name: en("results.evidence.summaryTitle"),
      }),
    ).toBeInTheDocument()
    expect(within(grounds).getByText("Covers most items by catalogue.")).toBeInTheDocument()
    expect(within(grounds).getByText(en("results.evidence.mainClarify"))).toBeInTheDocument()
    expect(within(grounds).getAllByText("Delivery terms.")).toHaveLength(2)
  })

  it("puts the strongest matches first and keeps the source beside each claim", async () => {
    const { user } = await openResults(recommendationFixture)
    const grounds = panel("North Foods")
    expect(within(grounds).getByText("5 of 5 items")).toBeInTheDocument()
    expect(within(grounds).getByText(en("results.evidence.matchesHint"))).toBeInTheDocument()
    const lists = within(grounds).getAllByRole("list")
    const matches = lists[0]
    if (!matches) throw new Error("match list is missing")
    const rows = within(matches).getAllByRole("listitem")
    expect(rows).toHaveLength(4)
    expect(
      within(rows[0] as HTMLElement).getByText(en("results.evidence.basis.stock")),
    ).toBeInTheDocument()
    expect(within(grounds).getByRole("link", { name: "Price list" })).toHaveAttribute(
      "href",
      "#price",
    )
    expect(within(grounds).getByText("checked Sep 28, 2026")).toBeInTheDocument()
    const toggle = within(grounds).getByRole("button", { name: "Show all (5)" })
    expect(toggle).toHaveAttribute("aria-expanded", "false")
    await user.click(toggle)
    expect(within(matches).getAllByRole("listitem")).toHaveLength(5)
    expect(within(matches).getByText(en("results.evidence.basis.inferred"))).toBeInTheDocument()
    expect(within(matches).getByText(en("results.evidence.noSource"))).toBeInTheDocument()
    await user.click(
      within(grounds).getByRole("button", { name: en("results.evidence.showLess") }),
    )
    expect(within(matches).getAllByRole("listitem")).toHaveLength(4)
  })

  it("separates past purchases from a promise of future ones", async () => {
    await openResults(recommendationFixture)
    const grounds = panel("North Foods")
    expect(within(grounds).getByText("11 similar purchases, wins: 4")).toBeInTheDocument()
    expect(within(grounds).getByText("Winner · 2024")).toBeInTheDocument()
    expect(within(grounds).getByRole("link", { name: "Protocol 42" })).toBeInTheDocument()
    expect(within(grounds).getByText(en("results.evidence.purchasesNote"))).toBeInTheDocument()
    expect(within(grounds).getByRole("button", { name: "Show all (3)" })).toBeInTheDocument()
  })

  it("switches to the chosen company and keeps its limits visible", async () => {
    const { user } = await openResults(recommendationFixture)
    await user.click(screen.getByRole("button", { name: new RegExp(LONG_NAME) }))
    expect(screen.getByRole("button", { name: new RegExp(LONG_NAME) })).toHaveAttribute(
      "aria-pressed",
      "true",
    )
    const grounds = panel(LONG_NAME)
    expect(
      within(grounds).getByRole("heading", {
        level: 3,
        name: en("results.evidence.checkTitle"),
      }),
    ).toBeInTheDocument()
    expect(
      within(grounds).queryByText(en("results.evidence.mainClarify")),
    ).not.toBeInTheDocument()
    expect(within(grounds).getAllByText(en("results.evidence.notFound"))).toHaveLength(3)
    expect(within(grounds).getByText(en("results.evidence.noPurchases"))).toBeInTheDocument()
    expect(within(grounds).getByText(en("results.evidence.noClarify"))).toBeInTheDocument()
  })

  it("ignores matches for products outside the request", async () => {
    const { user } = await openResults(recommendationFixture)
    await user.click(screen.getByRole("button", { name: /West Trade/ }))
    const grounds = panel("West Trade")
    expect(within(grounds).getByText("1 of 5 items")).toBeInTheDocument()
    expect(within(grounds).getAllByText(en("results.evidence.notFound"))).toHaveLength(4)
    expect(
      within(grounds).getByText("Role is not confirmed.", { selector: "li" }),
    ).toBeInTheDocument()
  })
})

describe("on a narrow screen", () => {
  it("brings the grounds into view after a company is chosen", async () => {
    const scroll = vi.fn()
    Object.assign(window, { matchMedia: vi.fn(() => ({ matches: true })) })
    Object.assign(HTMLElement.prototype, { scrollIntoView: scroll })
    const { user } = await openResults(recommendationFixture)
    await user.click(screen.getByRole("button", { name: /West Trade/ }))
    expect(window.matchMedia).toHaveBeenCalledWith(STACKED_LAYOUT)
    expect(scroll).toHaveBeenCalledWith({ block: "start" })
    Object.assign(window, { matchMedia: undefined })
  })
})
