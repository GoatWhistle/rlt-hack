import { screen, waitFor, within } from "@testing-library/react"
import { en } from "@tests/support/dictionaries"
import {
  lotSummary,
  renderPage,
  stubGateway,
  uploadDetail,
  uploadSummary,
} from "@tests/support/gateway"
import { describe, expect, it, vi } from "vitest"
import type { Company } from "@/entities/recommendation/model"
import { parseRecommendation } from "@/entities/recommendation/parse"
import { searchDraftPath } from "@/shared/config/paths"
import { recommendationFixture } from "../../entities/recommendation/fixture"
import { lotDetail, openLot } from "./open-lot"

const company: Company = {
  id: "historical",
  name: "Paper supplier",
  inn: "1111111111",
  role: "17.12",
  status: "historical",
  summary: "Paper procurement profile",
  matches: [],
  similarPurchases: null,
  wins: null,
  purchases: [],
  clarify: ["Check current availability"],
  history: {
    category: "17.12",
    lastDate: "2024-11-30",
    examples: ["Office paper", "Printing paper", "White paper", "Packaging paper"],
  },
  catalog: [{ name: "A4 paper", url: "https://example.test/paper", checkedAt: "2026-10-01" }],
  identitySource: "https://example.test/company",
}
const recommendation = { ...recommendationFixture, products: [], companies: [company] }

describe("historical supplier data", () => {
  it("parses history, catalog and company source", () => {
    expect(parseRecommendation(recommendation)).toEqual(recommendation)
  })
  it("shows actual examples and catalog without unsupported confirmation warnings", async () => {
    const { user } = await openLot(lotDetail({ recommendation }))
    expect(
      screen.getByRole("heading", { name: en("history.requestTitle", "lot") }),
    ).toBeInTheDocument()
    expect(
      screen.getByRole("link", { name: en("history.requestEdit", "lot") }),
    ).toHaveAttribute("href", searchDraftPath(recommendation.requestTitle))
    const panel = screen.getByRole("article", { name: company.name })
    expect(within(panel).getByText("Why this supplier was found")).toBeInTheDocument()
    expect(within(panel).getByText(/Latest procurement.*2024-11-30/)).toBeInTheDocument()
    expect(within(panel).getByText("Office paper")).toBeInTheDocument()
    expect(within(panel).getByRole("link", { name: /^A4 paper/ })).toHaveAttribute(
      "href",
      "https://example.test/paper",
    )
    expect(within(panel).queryByText(/No confirming sources/)).not.toBeInTheDocument()
    expect(screen.getByText("4 examples")).toBeInTheDocument()
    await user.click(within(panel).getByRole("button", { name: "Company profile" }))
    expect(
      within(screen.getByRole("dialog")).getByRole("link", { name: "Company page" }),
    ).toHaveAttribute("href", "https://example.test/company")
  })
  it("keeps absent catalog and history date absent", async () => {
    const sparse = {
      ...company,
      catalog: [],
      history: { category: "17.12", examples: ["Paper"], lastDate: "" },
    }
    await openLot(lotDetail({ recommendation: { ...recommendation, companies: [sparse] } }))
    expect(screen.queryByText("Published company products")).not.toBeInTheDocument()
    expect(screen.queryByText(/Latest procurement/)).not.toBeInTheDocument()
  })
})

describe("grounded procurement recommendations", () => {
  it("shows counts, products, dates, wins and source links", async () => {
    const grounded: Company = {
      ...company,
      status: "recommended",
      rankingReasons: ["relevance", "category"],
      similarPurchases: 12,
      wins: 4,
      purchases: [
        {
          title: "Paper for offices",
          year: 2024,
          date: "2024-11-01",
          customerInn: "2222222222",
          products: ["Paper A4"],
          outcome: "winner",
          source: { kind: "purchase", title: "Archive", url: "/api/evidence/one" },
        },
        { title: "Printing supplies", year: 2023, outcome: "participant" },
      ],
    }
    const data = { ...recommendation, companies: [grounded] }
    expect(parseRecommendation(data)).toEqual(data)
    await openLot(lotDetail({ recommendation: data }))
    const panel = screen.getByRole("article", { name: company.name })
    expect(
      within(panel).getByRole("heading", { name: "Grounds for this recommendation" }),
    ).toBeInTheDocument()
    expect(
      within(panel).getByRole("region", { name: "What raised this supplier in the ranking" }),
    ).toBeInTheDocument()
    expect(within(panel).getByText("Match with the request description")).toBeInTheDocument()
    expect(within(panel).getByText("12")).toBeInTheDocument()
    expect(within(panel).getByText("Paper A4")).toBeInTheDocument()
    expect(within(panel).getByText("2024-11-01")).toBeInTheDocument()
    expect(within(panel).getByText(/2222222222/)).toBeInTheDocument()
    expect(within(panel).getByRole("link", { name: /Open archive record/ })).toHaveAttribute(
      "href",
      "/api/evidence/one",
    )
    expect(within(panel).getByRole("link", { name: /^A4 paper/ })).toBeInTheDocument()
    expect(within(panel).queryByText("Key thing to clarify.")).not.toBeInTheDocument()
  })
})

describe("a text query result", () => {
  it("leads back to the query history and drops the lone pager and lot facts", async () => {
    const upload = uploadSummary({ fileName: "search.csv", title: "paper clip", total: 1 })
    const lot = lotSummary("query", { title: "paper clip" })
    const gateway = stubGateway({
      get: vi.fn(async () => uploadDetail([lot], upload)),
      lot: vi.fn(async () => lotDetail({ upload, lot, recommendation })),
    })
    renderPage("/uploads/u1/lots/query", gateway)
    await screen.findByRole("heading", { level: 1, name: "paper clip" })
    expect(screen.getByRole("link", { name: en("header.backQueries", "lot") })).toHaveAttribute(
      "href",
      "/history?tab=queries",
    )
    expect(
      screen.queryByRole("navigation", { name: en("header.neighbours", "lot") }),
    ).toBeNull()
    expect(screen.queryByText(/^Lot query$/)).toBeNull()
    await waitFor(() => expect(document.title).toBe("lotive | Search"))
  })
})
