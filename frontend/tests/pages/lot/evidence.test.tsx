import { screen, waitFor, within } from "@testing-library/react"
import { en } from "@tests/support/dictionaries"
import { afterEach, describe, expect, it, vi } from "vitest"
import type { Company } from "@/entities/recommendation/model"
import { resetShortlists } from "@/entities/shortlist/store"
import { NARROW_LAYOUT } from "@/shared/ui/workspace-layout"
import { LONG_NAME, recommendationFixture } from "../../entities/recommendation/fixture"
import { lotDetail, openLot } from "./open-lot"

afterEach(() => {
  resetShortlists()
  Object.assign(window, { matchMedia: undefined })
})

function panel(name: string | RegExp) {
  return screen.getByRole("article", { name })
}

function extraCompanies(count: number): Company[] {
  return Array.from({ length: count }, (_, index) => ({
    id: `extra-${index}`,
    name: `Extra ${index}`,
    inn: `78000009${index}0`,
    role: "Supplier",
    status: "recommended",
    summary: "Extra.",
    matches: [{ productId: "rice", basis: "catalog" }],
    similarPurchases: 0,
    wins: 0,
    purchases: [],
    clarify: [],
  }))
}

describe("the candidates column", () => {
  it("shows rank, match, history and a concrete reason to check", async () => {
    await openLot()
    const companies = screen.getByRole("region", { name: en("companies.title", "lot") })
    const north = within(companies).getByRole("button", { name: /North Foods/ })
    expect(north).toHaveAttribute("aria-pressed", "true")
    expect(within(north).getByText("5 of 5 · 11 purchases")).toBeInTheDocument()
    expect(
      within(north).getByRole("img", {
        name: "Match 5 of 5: stock confirmed — 1, in the catalogue — 3, assumed — 1",
      }),
    ).toBeInTheDocument()
    expect(within(north).getByText("01")).toBeInTheDocument()
    const south = within(companies).getByRole("button", { name: new RegExp(LONG_NAME) })
    expect(within(south).getByText("Range not confirmed")).toBeInTheDocument()
    const west = within(companies).getByRole("button", { name: /West Trade/ })
    expect(within(west).getByText(en("companies.status.check", "lot"))).toBeInTheDocument()
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
    expect(within(grounds).getByText("Tax ID 7800000011")).toBeInTheDocument()
    expect(within(grounds).getByText("5/5")).toBeInTheDocument()
    expect(
      within(grounds).getByRole("heading", {
        level: 3,
        name: en("evidence.summaryTitle", "lot"),
      }),
    ).toBeInTheDocument()
    expect(within(grounds).getByText(en("evidence.mainClarify", "lot"))).toBeInTheDocument()
    const confirmations = within(grounds)
      .getByRole("heading", { name: en("evidence.confirmations", "lot") })
      .closest("section")
    if (!confirmations) throw new Error("no confirmations")
    const rows = within(confirmations).getAllByRole("listitem")
    expect(rows).toHaveLength(3)
    expect(
      within(rows[0] as HTMLElement).getByText(en("evidence.basis.stock", "lot")),
    ).toBeInTheDocument()
    expect(within(confirmations).getByRole("link", { name: /^Price list/ })).toHaveAttribute(
      "href",
      "#price",
    )
    expect(within(confirmations).getByText("checked Sep 28, 2026")).toBeInTheDocument()
  })

  it("keeps details folded but complete", async () => {
    const { user } = await openLot()
    const grounds = panel("North Foods")
    await user.click(within(grounds).getByText(en("evidence.matchesTitle", "lot")))
    expect(within(grounds).getByText(en("evidence.basis.inferred", "lot"))).toBeVisible()
    expect(within(grounds).getByText(en("evidence.noSource", "lot"))).toBeVisible()
    await user.click(within(grounds).getByText(en("evidence.purchasesTitle", "lot")))
    expect(within(grounds).getByRole("link", { name: "Lot 42" })).toHaveAttribute("href", "#42")
    expect(within(grounds).getByText(en("evidence.purchasesNote", "lot"))).toBeVisible()
    await user.click(within(grounds).getByText(en("evidence.clarifyTitle", "lot")))
    expect(within(grounds).getByRole("checkbox", { name: "Delivery terms." })).not.toBeChecked()
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
    expect(within(grounds).getByText(en("evidence.noConfirmations", "lot"))).toBeInTheDocument()
    expect(
      within(grounds).getByText("No records for 4 products: Rice, Sugar, Salt, Oil"),
    ).toBeInTheDocument()
    await user.click(within(grounds).getByText(en("evidence.purchasesTitle", "lot")))
    expect(within(grounds).getByText(en("evidence.noPurchases", "lot"))).toBeVisible()
    await user.click(within(grounds).getByText(en("evidence.clarifyTitle", "lot")))
    expect(within(grounds).getByText(en("evidence.noClarify", "lot"))).toBeVisible()
  })
})

describe("choosing, comparing and the profile", () => {
  it("compares chosen candidates side by side", async () => {
    const { user } = await openLot()
    await user.click(
      within(panel("North Foods")).getByRole("button", { name: en("evidence.choose", "lot") }),
    )
    expect(
      within(panel("North Foods")).getByRole("button", { name: en("evidence.chosen", "lot") }),
    ).toBeInTheDocument()
    await user.click(screen.getByRole("button", { name: /West Trade/ }))
    await user.click(
      within(panel("West Trade")).getByRole("button", { name: en("evidence.choose", "lot") }),
    )
    await user.click(screen.getByRole("button", { name: "Compare chosen (2)" }))
    const dialog = await screen.findByRole("dialog", { name: en("compare.title", "lot") })
    const table = within(dialog).getByRole("table")
    expect(
      within(table)
        .getAllByRole("columnheader")
        .map((cell) => cell.textContent),
    ).toEqual([en("compare.criterion", "lot"), "North Foods", "West Trade"])
    const missing = within(table)
      .getByRole("rowheader", { name: en("compare.missing", "lot") })
      .closest("tr")
    expect(missing).toHaveTextContent("Rice, Sugar, Tea, Salt, Oil")
    expect(
      within(table)
        .getByRole("rowheader", { name: en("compare.contacts", "lot") })
        .closest("tr"),
    ).toHaveTextContent("No records")
    expect(within(dialog).getByText(en("compare.note", "lot"))).toBeInTheDocument()
    await user.click(within(dialog).getByRole("button", { name: en("action.close") }))
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull())
    expect(screen.getAllByText(en("companies.chosen", "lot"))).toHaveLength(2)
  })

  it("opens the company profile with requisites, contacts and sources", async () => {
    const recommendation = {
      ...recommendationFixture,
      companies: recommendationFixture.companies.map((company, index) =>
        index === 0
          ? {
              ...company,
              contacts: {
                site: "https://north.example",
                email: "a@north.example",
                phone: "+7 (812) 1",
              },
              roleSource: { kind: "registry" as const, title: "Registry card", url: "#reg" },
            }
          : company,
      ),
    }
    const { user } = await openLot(lotDetail({ recommendation }))
    await user.click(screen.getByRole("button", { name: en("evidence.profile", "lot") }))
    const profile = await screen.findByRole("dialog", { name: "North Foods" })
    expect(within(profile).getByRole("link", { name: "a@north.example" })).toHaveAttribute(
      "href",
      "mailto:a@north.example",
    )
    expect(within(profile).getByRole("link", { name: "+7 (812) 1" })).toHaveAttribute(
      "href",
      "tel:+78121",
    )
    expect(within(profile).getAllByRole("link", { name: /^Registry card/ })).toHaveLength(2)
    expect(within(profile).getByRole("link", { name: /^Price list/ })).toBeInTheDocument()
    expect(within(profile).getByText("11 similar · wins: 4")).toBeInTheDocument()
  })

  it("says when a profile has no contacts, role basis or sources", async () => {
    const { user } = await openLot()
    await user.click(screen.getByRole("button", { name: new RegExp(LONG_NAME) }))
    await user.click(screen.getByRole("button", { name: en("evidence.profile", "lot") }))
    const profile = await screen.findByRole("dialog")
    expect(within(profile).getByText(en("profile.noContacts", "lot"))).toBeInTheDocument()
    expect(within(profile).getByText(en("profile.noRoleBasis", "lot"))).toBeInTheDocument()
    expect(within(profile).getByText(en("profile.noSources", "lot"))).toBeInTheDocument()
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
    const { user } = await openLot()
    expect(matchMedia).toHaveBeenCalledWith(NARROW_LAYOUT)
    expect(screen.getByRole("radio", { name: en("views.evidence", "lot") })).toBeChecked()
    expect(screen.queryByRole("region", { name: en("products.title", "lot") })).toBeNull()
    await user.click(screen.getByRole("radio", { name: en("views.products", "lot") }))
    await user.click(screen.getByRole("button", { name: "Show candidates with “Tea”" }))
    expect(screen.getByRole("radio", { name: en("views.companies", "lot") })).toBeChecked()
    await user.click(screen.getByRole("button", { name: new RegExp(LONG_NAME) }))
    expect(screen.getByRole("article", { name: LONG_NAME })).toBeInTheDocument()
  })
})
