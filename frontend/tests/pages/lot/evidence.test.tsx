import { screen, within } from "@testing-library/react"
import { en } from "@tests/support/dictionaries"
import { afterEach, describe, expect, it, vi } from "vitest"
import type { Company } from "@/entities/recommendation/model"
import { resetShortlists } from "@/entities/shortlist/store"
import { NARROW_LAYOUT } from "@/pages/lot/workspace"
import { LONG_NAME, recommendationFixture } from "../../entities/recommendation/fixture"
import { lotDetail, openLot, panel } from "./open-lot"

afterEach(() => {
  resetShortlists()
  Object.assign(window, { matchMedia: undefined })
})

function extraCompanies(count: number): Company[] {
  return Array.from({ length: count }, (_, index) => ({
    id: `extra-${index}`,
    name: `Extra ${index}`,
    inn: `78000009${index}0`,
    role: "supplier",
    status: "recommended",
    checkReasons: [],
    highlights: [],
    matches: [{ productId: "rice", basis: "catalog" }],
    similarPurchases: 0,
    wins: 0,
    purchases: [],
  }))
}

describe("the candidates column", () => {
  it("shows rank, match, history and a concrete reason to check", async () => {
    await openLot()
    const companies = screen.getByRole("region", { name: en("companies.title", "lot") })
    const north = within(companies).getByRole("button", { name: /North Foods/ })
    expect(north).toHaveAttribute("aria-pressed", "true")
    expect(within(north).getByText("11 purchases")).toBeInTheDocument()
    const score = within(north).getByText("4/5")
    expect(score).toHaveAttribute("aria-hidden", "true")
    expect(score).toHaveTextContent("4/5+1")
    expect(
      within(north).getByRole("img", {
        name: "Match 5 of 5: stock confirmed — 1, in the catalog — 3, assumed — 1",
      }),
    ).toBeInTheDocument()
    expect(within(north).getByText("01")).toBeInTheDocument()
    const south = within(companies).getByRole("button", { name: new RegExp(LONG_NAME) })
    expect(within(south).getByText("Product range not confirmed")).toBeInTheDocument()
    const west = within(companies).getByRole("button", { name: /West Trade/ })
    expect(within(west).getByText(en("status.check", "evidence"))).toBeInTheDocument()
    expect(within(companies).getByText(en("companies.compareHint", "lot"))).toBeInTheDocument()
  })

  it("shows the first candidates and the rest on request", async () => {
    const recommendation = {
      ...recommendationFixture,
      companies: [...recommendationFixture.companies, ...extraCompanies(3)],
    }
    const { user } = await openLot(lotDetail({ recommendation }))
    const companies = screen.getByRole("region", { name: en("companies.title", "lot") })
    expect(within(companies).getAllByRole("button", { pressed: false })).toHaveLength(3)
    await user.click(within(companies).getByRole("button", { name: "Show 2 more" }))
    expect(within(companies).getByRole("button", { name: /Extra 2/ })).toBeInTheDocument()
    await user.click(
      within(companies).getByRole("button", { name: en("companies.showLess", "lot") }),
    )
    expect(within(companies).queryByRole("button", { name: /Extra 2/ })).toBeNull()
  })
})

describe("the grounds panel", () => {
  it("leads with the reason, the main caveat and key confirmations with sources", async () => {
    await openLot()
    const grounds = panel("North Foods")
    expect(within(grounds).getByText("INN 7800000011")).toBeInTheDocument()
    expect(within(grounds).getByText("4/5")).toBeInTheDocument()
    expect(within(grounds).getByText("+1 assumption")).toBeInTheDocument()
    expect(
      within(grounds).getByRole("heading", {
        level: 3,
        name: en("evidence.summaryTitle", "lot"),
      }),
    ).toBeInTheDocument()
    expect(
      within(grounds).getByText(
        "Covers 5 of 5 items · In stock for 1 item · 4 wins in similar purchases",
      ),
    ).toBeInTheDocument()
    expect(
      within(grounds).getByText(en("evidence.mainClarify", "lot")).parentElement,
    ).toHaveTextContent("Confirm availability and price: Rice")
    const confirmations = within(grounds)
      .getByRole("heading", { name: en("evidence.confirmations", "lot") })
      .closest("section")
    if (!confirmations) throw new Error("no confirmations")
    const rows = within(confirmations).getAllByRole("listitem")
    expect(rows).toHaveLength(3)
    expect(
      within(rows[0] as HTMLElement).getByText(en("basis.stock", "evidence")),
    ).toBeInTheDocument()
    const price = within(confirmations).getByRole("link", { name: /^Price list/ })
    expect(price).toHaveAttribute("href", "#price")
    expect(price).toHaveAttribute("target", "_blank")
    expect(price).toHaveAttribute("rel", "noopener noreferrer")
    expect(price).toHaveAccessibleName("Price list (opens in a new tab)")
    expect(within(confirmations).getByText("checked Sep 28, 2026")).toBeInTheDocument()
  })

  it("keeps details folded but complete", async () => {
    const { user } = await openLot()
    const grounds = panel("North Foods")
    await user.click(within(grounds).getByText(en("evidence.matchesTitle", "lot")))
    expect(within(grounds).getByText(en("basis.inferred", "evidence"))).toBeVisible()
    expect(within(grounds).getByText(en("noSource", "evidence"))).toBeVisible()
    await user.click(within(grounds).getByText(en("evidence.purchasesTitle", "lot")))
    expect(within(grounds).getByRole("link", { name: "Lot 42 · Food supply" })).toHaveAttribute(
      "href",
      "#42",
    )
    expect(within(grounds).getByText(en("evidence.purchasesNote", "lot"))).toBeVisible()
    await user.click(within(grounds).getByText(en("evidence.clarifyTitle", "lot")))
    expect(within(grounds).queryByRole("checkbox")).toBeNull()
    const clarify = within(grounds)
      .getByText(en("evidence.clarifyTitle", "lot"))
      .closest("details") as HTMLElement
    expect(
      within(clarify)
        .getAllByRole("listitem")
        .map((item) => item.textContent),
    ).toEqual([
      "Confirm availability and price: Rice",
      "Confirm availability and price: Sugar",
      "Confirm availability and price: Salt",
      "Confirm availability and price: Oil",
    ])
  })

  it("does not hide missing records or missing sources", async () => {
    const { user } = await openLot()
    await user.click(screen.getByRole("button", { name: new RegExp(LONG_NAME) }))
    const grounds = panel(LONG_NAME)
    expect(
      within(grounds).getByRole("heading", {
        level: 3,
        name: en("evidence.checkTitle", "lot"),
      }),
    ).toBeInTheDocument()
    expect(
      within(grounds).getByText(en("checkReason.rangeUnconfirmed", "evidence")),
    ).toBeInTheDocument()
    expect(within(grounds).getByText(en("evidence.noConfirmations", "lot"))).toBeInTheDocument()
    expect(
      within(grounds).getByText("No records for 4 products: Rice, Sugar, Salt, and Oil"),
    ).toBeInTheDocument()
    await user.click(within(grounds).getByText(en("evidence.purchasesTitle", "lot")))
    expect(within(grounds).getByText(en("evidence.noPurchases", "lot"))).toBeVisible()
    await user.click(within(grounds).getByText(en("evidence.clarifyTitle", "lot")))
    const clarify = within(grounds)
      .getByText(en("evidence.clarifyTitle", "lot"))
      .closest("details") as HTMLElement
    expect(
      within(clarify).getByText(en("clarify.reason.rangeUnconfirmed", "lot")),
    ).toBeVisible()
    expect(within(clarify).getByText("Confirm availability and price: Tea")).toBeVisible()
  })

  it("says when there is nothing to report or clarify", async () => {
    const { user } = await openLot()
    await user.click(screen.getByRole("button", { name: /West Trade/ }))
    const grounds = panel("West Trade")
    expect(within(grounds).getByText(en("evidence.noHighlights", "lot"))).toBeInTheDocument()
    expect(within(grounds).queryByText(en("evidence.mainClarify", "lot"))).toBeNull()
    await user.click(within(grounds).getByText(en("evidence.clarifyTitle", "lot")))
    expect(within(grounds).getByText(en("evidence.noClarify", "lot"))).toBeVisible()
  })

  it("says the INN is unknown when the company has none", async () => {
    const recommendation = {
      ...recommendationFixture,
      companies: recommendationFixture.companies.map((company, index) =>
        index === 0 ? { ...company, inn: "" } : company,
      ),
    }
    await openLot(lotDetail({ recommendation }))
    const grounds = panel("North Foods")
    expect(within(grounds).getByText(en("noInn", "evidence"))).toBeInTheDocument()
    expect(within(grounds).queryByText(/^INN $/)).toBeNull()
  })
})

describe("on a narrow screen", () => {
  it("shows one section at a time and moves to the grounds after a choice", async () => {
    const matchMedia = vi.fn(() => ({
      matches: true,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    }))
    Object.assign(window, { matchMedia })
    const scrollBy = vi.fn()
    Object.assign(window, { scrollBy })
    const { user } = await openLot()
    expect(matchMedia).toHaveBeenCalledWith(NARROW_LAYOUT)
    expect(screen.getByRole("radio", { name: en("views.evidence", "lot") })).toBeChecked()
    expect(screen.queryByRole("region", { name: en("products.title", "lot") })).toBeNull()
    const stack = screen.getByRole("group", { name: en("views.legend", "lot") }).parentElement
      ?.parentElement as HTMLElement
    vi.spyOn(stack, "getBoundingClientRect").mockReturnValue({ top: -120 } as DOMRect)
    await user.click(screen.getByRole("radio", { name: en("views.products", "lot") }))
    expect(scrollBy).toHaveBeenCalledWith({ top: -120 })
    expect(screen.getByRole("radio", { name: en("views.products", "lot") })).toHaveFocus()
    await user.click(screen.getByRole("button", { name: "Show candidates with “Tea”" }))
    expect(screen.getByRole("radio", { name: en("views.candidates", "lot") })).toBeChecked()
    expect(
      screen.getByRole("heading", { level: 2, name: en("companies.title", "lot") }),
    ).toHaveFocus()
    await user.click(screen.getByRole("button", { name: new RegExp(LONG_NAME) }))
    expect(screen.getByRole("article", { name: LONG_NAME })).toBeInTheDocument()
    expect(screen.getByRole("heading", { level: 2, name: LONG_NAME })).toHaveFocus()
  })
})
