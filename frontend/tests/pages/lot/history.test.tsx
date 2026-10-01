import { screen, within } from "@testing-library/react"
import { describe, expect, it } from "vitest"
import type { Company } from "@/entities/recommendation/model"
import { parseRecommendation } from "@/entities/recommendation/parse"
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
    expect(screen.getByRole("heading", { name: "Search by description" })).toBeInTheDocument()
    const panel = screen.getByRole("article", { name: company.name })
    expect(within(panel).getByText("Why this supplier was found")).toBeInTheDocument()
    expect(within(panel).getByText(/Latest procurement.*2024-11-30/)).toBeInTheDocument()
    expect(within(panel).getByText("Office paper")).toBeInTheDocument()
    expect(within(panel).getByRole("link", { name: "A4 paper" })).toHaveAttribute(
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
