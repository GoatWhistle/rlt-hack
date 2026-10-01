import { screen, within } from "@testing-library/react"
import { en, text } from "@tests/support/dictionaries"
import { afterEach, describe, expect, it, vi } from "vitest"
import { CSV_TYPE } from "@/pages/results/result-header"
import * as download from "@/shared/download/save-text-file"
import { LONG_NAME, recommendationFixture } from "../../entities/recommendation/fixture"
import { openResults } from "./open-results"

function spanWithText(text: string) {
  return (_: string, element: Element | null) =>
    element?.tagName === "SPAN" && element.textContent === text
}

afterEach(() => {
  vi.restoreAllMocks()
})

describe("the results header", () => {
  it("names the request once and sums up the search", async () => {
    await openResults(recommendationFixture)
    expect(screen.getByRole("heading", { level: 1, name: "Food supply" })).toBeInTheDocument()
    expect(screen.getByText("Lot 1")).toBeInTheDocument()
    expect(screen.getByText("lot.xlsx")).toBeInTheDocument()
    expect(screen.getByText(spanWithText("5 products"))).toBeInTheDocument()
    expect(screen.getByText(spanWithText("3 candidates"))).toBeInTheDocument()
    expect(screen.getByText(spanWithText("2 need checking"))).toBeInTheDocument()
    const chain = screen.getByRole("list", { name: en("results.chain.label") })
    expect(within(chain).getAllByRole("listitem")).toHaveLength(4)
    expect(within(chain).getByText(en("results.chain.evidence"))).toHaveAttribute(
      "aria-current",
      "step",
    )
  })

  it("exports the candidates as csv", async () => {
    const save = vi.spyOn(download, "saveTextFile").mockImplementation(() => {})
    const { user } = await openResults(recommendationFixture)
    await user.click(screen.getByRole("button", { name: en("results.header.downloadCsv") }))
    const [name, content, type] = save.mock.calls[0] ?? []
    expect(name).toBe("lot-suppliers.csv")
    expect(type).toBe(CSV_TYPE)
    expect(content).toContain("1;North Foods;7800000011;Supplier;Recommended;5/5;11;4;")
    expect(content).toContain("Range not confirmed;1/5;1;0")
    expect(content).toContain("West Trade;7800000033;Distributor;Needs checking;1/5")
  })
})

describe("the products column", () => {
  it("labels the origin briefly and explains it on demand", async () => {
    const { user } = await openResults(recommendationFixture)
    const products = screen.getByRole("region", { name: en("results.products.title") })
    expect(within(products).getAllByText(en("results.products.origin.notice"))).toHaveLength(3)
    expect(
      within(products).getByText(en("results.products.origin.inferred")),
    ).toBeInTheDocument()
    expect(within(products).getByText(en("results.products.origin.user"))).toBeInTheDocument()
    const sugar = within(products).getByText("Sugar").closest("details")
    expect(sugar).not.toHaveAttribute("open")
    await user.click(within(products).getByText("Sugar"))
    expect(sugar).toHaveAttribute("open")
    expect(within(products).getByText("Seen in 8 of 10 similar purchases.")).toBeVisible()
    expect(
      within(products).getByText(en("results.products.originNote.user"), { selector: "p" }),
    ).toBeInTheDocument()
  })
})

describe("the companies column", () => {
  it("shows the rank, match, history and a concrete reason to check", async () => {
    await openResults(recommendationFixture)
    const companies = screen.getByRole("region", { name: en("results.companies.title") })
    const north = within(companies).getByRole("button", { name: /North Foods/ })
    expect(north).toHaveAttribute("aria-pressed", "true")
    expect(within(north).getByText("5 of 5 · 11 purchases")).toBeInTheDocument()
    expect(
      within(north).getByRole("img", {
        name: "Match 5 of 5: stock confirmed — 1, in the catalogue — 3, assumed — 1",
      }),
    ).toBeInTheDocument()
    expect(within(north).getByText("01")).toBeInTheDocument()
    expect(within(north).queryByText(/7800000011/)).not.toBeInTheDocument()
    const south = within(companies).getByRole("button", { name: new RegExp(LONG_NAME) })
    expect(within(south).getByText("Range not confirmed")).toBeInTheDocument()
    expect(within(south).getByText("1 of 5 · 1 purchase")).toBeInTheDocument()
    const west = within(companies).getByRole("button", { name: /West Trade/ })
    expect(within(west).getByText(en("results.companies.status.check"))).toBeInTheDocument()
  })

  it("speaks russian with the right plural forms", async () => {
    await openResults(recommendationFixture, { locale: "ru" })
    expect(screen.getByText(spanWithText("5 товаров"))).toBeInTheDocument()
    expect(screen.getByText(spanWithText("3 кандидата"))).toBeInTheDocument()
    expect(screen.getByText(spanWithText("2 требуют проверки"))).toBeInTheDocument()
    expect(screen.getByText("5 из 5 · 11 закупок")).toBeInTheDocument()
    expect(screen.getByText("5 позиций")).toBeInTheDocument()
    expect(
      screen.getByText(text("ru", "common", "results.evidence.summaryTitle")),
    ).toBeInTheDocument()
  })
})

describe("without a result", () => {
  it("offers to upload a file", async () => {
    await openResults({ broken: true })
    expect(
      screen.getByRole("heading", { level: 1, name: en("results.empty.title") }),
    ).toBeInTheDocument()
    expect(screen.getByRole("link", { name: en("results.empty.action") })).toHaveAttribute(
      "href",
      "/",
    )
  })
})
