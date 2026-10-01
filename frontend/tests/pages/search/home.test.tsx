import { screen, waitFor, within } from "@testing-library/react"
import { en } from "@tests/support/dictionaries"
import { contract, contractResult, renderSearch, stubSearch } from "@tests/support/search"
import { describe, expect, it, vi } from "vitest"
import { parseRecentSearches } from "@/entities/search/parse"
import { ApiError } from "@/shared/api/api-error"

function recentRegion() {
  return screen.getByRole("region", { name: en("recent.title", "search") })
}

describe("the search page", () => {
  it("invites a description and says when there are no searches yet", async () => {
    renderSearch("/search")
    expect(
      screen.getByRole("heading", { level: 1, name: en("home.title", "search") }),
    ).toBeInTheDocument()
    const guide = await screen.findByRole("region", { name: en("guide.title", "search") })
    expect(within(guide).getByText(en("guide.inferred", "search"))).toBeVisible()
    expect(screen.queryByRole("region", { name: en("recent.title", "search") })).toBeNull()
  })

  it("lists recent searches as links to their results", async () => {
    const recent = vi.fn(async () =>
      parseRecentSearches(contract("search/recent.example.json")),
    )
    renderSearch("/search", { gateway: stubSearch({ recent }) })
    const link = await within(recentRegion()).findByRole("link", { name: /Крупа гречневая/ })
    expect(link).toHaveAttribute("href", "/search/1f0c3b5e-6a1d-4c2e-9f7a-2b8d4e6f1a90")
    expect(link).toHaveTextContent("2 items · 2 candidates · 1 recommended")
  })

  it("offers to retry when the recent searches fail to load", async () => {
    const recent = vi
      .fn()
      .mockRejectedValueOnce(new ApiError({ status: 400, code: "invalid_limit" }))
      .mockResolvedValue([])
    const { user } = renderSearch("/search", { gateway: stubSearch({ recent }) })
    const alert = await within(recentRegion()).findByRole("alert")
    expect(alert).toHaveTextContent(en("invalid_limit", "errors"))
    await user.click(within(alert).getByRole("button", { name: en("recent.retry", "search") }))
    expect(
      await screen.findByRole("region", { name: en("guide.title", "search") }),
    ).toBeVisible()
  })

  it("prefills a query from the address and opens the result after the search", async () => {
    const gateway = stubSearch()
    const { user, router } = renderSearch("/search?q=buckwheat%20500%20kg", { gateway })
    const field = screen.getByRole("textbox", { name: en("box.label", "search") })
    expect(field).toHaveValue("buckwheat 500 kg")
    await user.type(field, "{Enter}")
    expect(gateway.search).toHaveBeenCalledWith(
      expect.objectContaining({ text: "buckwheat 500 kg" }),
    )
    await waitFor(() =>
      expect(router.state.location.pathname).toBe(`/search/${contractResult().searchId}`),
    )
  })
})
