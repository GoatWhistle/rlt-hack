import { screen, within } from "@testing-library/react"
import { en } from "@tests/support/dictionaries"
import { renderWithProviders } from "@tests/support/render"
import { Route, Routes, useNavigate } from "react-router"
import { describe, expect, it } from "vitest"
import { ResultsPage } from "@/pages/results"
import { recommendationFixture } from "../entities/recommendation/fixture"

function Opener({ state }: { readonly state: unknown }) {
  const navigate = useNavigate()
  return (
    <button type="button" onClick={() => navigate("/results", { state })}>
      open
    </button>
  )
}

async function openResults(state: unknown) {
  const view = renderWithProviders(
    <Routes>
      <Route path="/" element={<Opener state={state} />} />
      <Route path="/results" element={<ResultsPage />} />
    </Routes>,
  )
  await view.user.click(screen.getByRole("button", { name: "open" }))
  return view
}

describe("the results page", () => {
  it("shows the chain, products, companies and grounds of the first company", async () => {
    await openResults(recommendationFixture)
    expect(screen.getByRole("heading", { level: 1, name: "Food supply" })).toBeInTheDocument()
    const chain = screen.getByRole("list", { name: en("results.chain.label") })
    expect(within(chain).getByText("3 items")).toBeInTheDocument()
    expect(
      within(chain).getByText("1 from the notice · 1 inferred · 1 confirmed"),
    ).toBeInTheDocument()
    expect(within(chain).getByText("1 source · 1 to clarify")).toBeInTheDocument()
    expect(screen.getByText(en("results.products.origin.inferred"))).toBeInTheDocument()
    expect(screen.getByText("1 similar purchase")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /North Foods/ })).toHaveAttribute(
      "aria-pressed",
      "true",
    )
    expect(screen.getByRole("link", { name: "Groceries page" })).toHaveAttribute(
      "href",
      "#rice",
    )
    const coverage = screen.getByRole("list", { name: en("results.evidence.coverage") })
    expect(
      within(coverage).getAllByRole("img", { name: en("results.evidence.covered") }),
    ).toHaveLength(2)
    expect(
      within(coverage).getByRole("img", { name: en("results.evidence.missing") }),
    ).toBeInTheDocument()
  })

  it("switches the grounds to the chosen company", async () => {
    const { user } = await openResults(recommendationFixture)
    await user.click(screen.getByRole("button", { name: /South Trade/ }))
    expect(screen.getByRole("button", { name: /South Trade/ })).toHaveAttribute(
      "aria-pressed",
      "true",
    )
    expect(screen.getByText("Role is not confirmed.")).toBeInTheDocument()
    expect(screen.getByText("2 sources · 2 to clarify")).toBeInTheDocument()
  })

  it("offers to upload a file when there is no result", async () => {
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
