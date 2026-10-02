import { screen, waitFor, within } from "@testing-library/react"
import { en } from "@tests/support/dictionaries"
import { contract, renderSearch, stubSearch } from "@tests/support/search"
import { describe, expect, it, vi } from "vitest"
import { parseRecentSearches } from "@/entities/search/parse"
import { ageOf, isRecentDay } from "@/pages/search/recent-list/history-groups"
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
    expect(link).toHaveTextContent("2 items 2 candidates 1 recommended")
    expect(link).not.toHaveTextContent("·")
  })

  it("groups recent searches by how long ago they ran and marks empty ones", async () => {
    const [first] = parseRecentSearches(contract("search/recent.example.json"))
    if (!first) throw new Error("the contract example has no searches")
    const daysAgo = (days: number) => new Date(Date.now() - days * 86_400_000).toISOString()
    const recent = vi.fn(async () => [
      { ...first, searchId: "today", text: "Paper", createdAt: daysAgo(0) },
      { ...first, searchId: "yesterday", text: "Rice", createdAt: daysAgo(1) },
      {
        ...first,
        searchId: "empty",
        text: "Tractor",
        candidates: 0,
        recommended: 0,
        createdAt: daysAgo(3),
      },
    ])
    renderSearch("/search", { gateway: stubSearch({ recent }) })
    const region = recentRegion()
    const group = async (name: string) =>
      within(region)
        .findByRole("heading", { name })
        .then((heading) => within(heading.parentElement as HTMLElement).getByRole("link"))
    expect(await group("Today")).toHaveTextContent("Paper")
    expect(await group("Yesterday")).toHaveTextContent("Rice")
    expect(await group("3 days ago")).toHaveTextContent(en("recent.none", "search"))
  })

  it("keeps the whole history and loads older searches on demand", async () => {
    const [first] = parseRecentSearches(contract("search/recent.example.json"))
    if (!first) throw new Error("the contract example has no searches")
    const older = { ...first, searchId: "older", text: "Paper" }
    const history = vi
      .fn()
      .mockResolvedValueOnce({ searches: [first], hasMore: true, total: 2 })
      .mockResolvedValueOnce({ searches: [older], hasMore: false, total: 2 })
    const { user } = renderSearch("/search", { gateway: stubSearch({ history }) })
    const more = await within(recentRegion()).findByRole("button", { name: "Show 1 more" })
    await user.click(more)
    expect(await within(recentRegion()).findByRole("link", { name: /Paper/ })).toBeVisible()
    expect(history).toHaveBeenLastCalledWith(20, first.searchId)
    expect(within(recentRegion()).queryByRole("button", { name: /more/ })).toBeNull()
  })

  it("tells how long ago a search ran in days, weeks, months and years", () => {
    const now = new Date(2026, 9, 2, 12)
    const at = (...parts: [number, number, number]) => new Date(...parts, 9).toISOString()
    expect(ageOf(at(2026, 9, 2), now)).toEqual({ unit: "day", value: -0 })
    expect(ageOf(at(2026, 9, 1), now)).toEqual({ unit: "day", value: -1 })
    expect(isRecentDay(ageOf(at(2026, 9, 1), now))).toBe(true)
    expect(isRecentDay(ageOf(at(2026, 8, 29), now))).toBe(false)
    expect(ageOf(at(2026, 8, 24), now)).toEqual({ unit: "week", value: -1 })
    expect(ageOf(at(2026, 8, 15), now)).toEqual({ unit: "week", value: -2 })
    expect(ageOf(at(2026, 7, 20), now)).toEqual({ unit: "month", value: -2 })
    expect(ageOf(at(2025, 3, 1), now)).toEqual({ unit: "year", value: -1 })
    expect(ageOf(at(2026, 9, 5), now)).toEqual({ unit: "day", value: -0 })
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
    const { user, router, uploads } = renderSearch("/search?q=buckwheat%20500%20kg")
    const field = screen.getByRole("textbox", { name: en("box.label", "search") })
    expect(field).toHaveValue("buckwheat 500 kg")
    await user.click(screen.getByRole("button", { name: en("box.submit", "search") }))
    expect(uploads.create).toHaveBeenCalledWith(
      expect.objectContaining({
        check: expect.objectContaining({
          notices: [expect.objectContaining({ title: "buckwheat 500 kg" })],
        }),
      }),
    )
    await waitFor(() => expect(router.state.location.pathname).toBe("/uploads/u1/lots/query"))
  })

  it("hides recent searches upward, widens the field and remembers the choice", async () => {
    window.localStorage.clear()
    const recent = vi.fn(async () =>
      parseRecentSearches(contract("search/recent.example.json")),
    )
    const { user } = renderSearch("/search", { gateway: stubSearch({ recent }) })
    await within(recentRegion()).findByRole("link", { name: /Крупа гречневая/ })
    expect(screen.queryByRole("button", { name: /^Recent searches/ })).toBeNull()
    await user.click(screen.getByRole("button", { name: en("recent.collapse", "search") }))
    const reveal = screen.getByRole("button", { name: /^Recent searches/ })
    expect(reveal).toHaveAttribute("aria-expanded", "false")
    expect(reveal).toHaveFocus()
    expect(window.localStorage.getItem("lotive.search.recentOpen")).toBe("false")
    await user.click(reveal)
    expect(screen.queryByRole("button", { name: /^Recent searches/ })).toBeNull()
    expect(window.localStorage.getItem("lotive.search.recentOpen")).toBe("true")
  })

  it("prefers Saint Petersburg unless the address names a region or none", async () => {
    const trigger = () => screen.findByRole("button", { name: /^Delivery region:/ })
    const first = renderSearch("/search")
    expect(await trigger()).toHaveAccessibleName("Delivery region: Saint Petersburg")
    first.unmount()
    const second = renderSearch("/search?region=77")
    expect(await trigger()).toHaveAccessibleName("Delivery region: Moscow")
    second.unmount()
    renderSearch("/search?region=")
    expect(await trigger()).toHaveAccessibleName(
      `Delivery region: ${en("box.anyRegion", "search")}`,
    )
  })
})
