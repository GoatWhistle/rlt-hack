import { screen, waitFor, within } from "@testing-library/react"
import { en } from "@tests/support/dictionaries"
import { afterEach, describe, expect, it } from "vitest"
import { resetShortlists } from "@/entities/shortlist/store"
import { LONG_NAME, recommendationFixture } from "../../entities/recommendation/fixture"
import { lotDetail, openLot, panel } from "./open-lot"

afterEach(() => {
  resetShortlists()
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
    const headers = within(table).getAllByRole("columnheader")
    expect(headers.map((cell) => cell.firstChild?.textContent)).toEqual([
      en("compare.criterion", "lot"),
      "North Foods",
      "West Trade",
    ])
    expect(headers[1]).toHaveTextContent(en("role.supplier", "evidence"))
    const missing = within(table)
      .getByRole("rowheader", { name: en("compare.missing", "lot") })
      .closest("tr")
    expect(missing).toHaveTextContent("Rice, Sugar, Tea, Salt, and Oil")
    const clarify = within(table)
      .getByRole("rowheader", { name: en("compare.clarify", "lot") })
      .closest("tr")
    expect(clarify).toHaveTextContent("Confirm availability and price: Rice")
    expect(clarify).toHaveTextContent(en("compare.none", "lot"))
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
    expect(within(profile).getAllByRole("link", { name: "Registry card" })).toHaveLength(2)
    expect(within(profile).getByRole("link", { name: "Price list" })).toBeInTheDocument()
    expect(within(profile).getByText("11 similar · wins: 4")).toBeInTheDocument()
  })

  it("says when a profile has no contacts, role basis or sources", async () => {
    const { user } = await openLot()
    await user.click(screen.getByRole("button", { name: new RegExp(LONG_NAME) }))
    await user.click(screen.getByRole("button", { name: en("evidence.profile", "lot") }))
    const profile = await screen.findByRole("dialog")
    expect(within(profile).getByText(en("contacts.none", "evidence"))).toBeInTheDocument()
    expect(within(profile).getByText(en("profile.noRoleBasis", "lot"))).toBeInTheDocument()
    expect(within(profile).getByText(en("profile.noSources", "lot"))).toBeInTheDocument()
  })
})
