import { screen, waitFor, within } from "@testing-library/react"
import {
  meta,
  overview,
  ratio,
  renderAnalytics,
  source,
  stubAnalytics,
} from "@tests/support/analytics"
import { en } from "@tests/support/dictionaries"
import { describe, expect, it, vi } from "vitest"
import { ApiError } from "@/shared/api/api-error"

const t = (path: string) => en(path, "analytics")

describe("the analytics overview", () => {
  it("shows the four figures with their bases and the snapshot time", async () => {
    renderAnalytics("/analytics", stubAnalytics())
    expect(
      await screen.findByRole("heading", { level: 1, name: t("title") }),
    ).toBeInTheDocument()
    const fresh = await screen.findByRole("region", { name: t("metrics.fresh") })
    expect(within(fresh).getByText("67%")).toBeInTheDocument()
    expect(within(fresh).getByText("6 of 9")).toBeInTheDocument()
    expect(within(fresh).getByText("1 with an unknown date")).toBeInTheDocument()
    expect(within(fresh).getByRole("link", { name: t("records.show") })).toHaveAttribute(
      "href",
      "/analytics/records?problem=stale",
    )
    const offers = screen.getByRole("region", { name: t("metrics.offers") })
    expect(within(offers).getByText("10")).toBeInTheDocument()
    expect(within(offers).getByRole("link", { name: t("records.show") })).toHaveAttribute(
      "href",
      "/analytics/records",
    )
    expect(screen.getByText(/Snapshot:/)).toBeInTheDocument()
  })

  it("explains what needs attention and links to the data behind it", async () => {
    renderAnalytics("/analytics", stubAnalytics())
    expect(await screen.findByText("The last run of Source a failed")).toBeInTheDocument()
    const links = screen.getAllByRole("link", { name: t("attention.details") })
    expect(links[0]).toHaveAttribute("href", "/analytics/sources?source=a")
    expect(links[1]).toHaveAttribute("href", "/analytics/records?problem=no_category")
    expect(screen.getByText("4 of 10 offers have no category")).toBeInTheDocument()
  })

  it("says there is nothing to fix when the list is empty", async () => {
    renderAnalytics(
      "/analytics",
      stubAnalytics({ overview: vi.fn(async () => overview({ attention: [] })) }),
    )
    expect(await screen.findByText(t("attention.none"))).toBeInTheDocument()
  })

  it("shows no base instead of a fake zero", async () => {
    const empty = overview({ searchable: ratio(0, 0) })
    renderAnalytics("/analytics", stubAnalytics({ overview: vi.fn(async () => empty) }))
    const card = await screen.findByRole("region", { name: t("metrics.searchable") })
    expect(within(card).getByText(t("ratio.noBase"))).toBeInTheDocument()
    expect(within(card).queryByText("0%")).toBeNull()
  })

  it("keeps the filters in the address and sends them to the gateway", async () => {
    const gateway = stubAnalytics()
    const { user, router } = renderAnalytics("/analytics", gateway)
    await screen.findByRole("region", { name: t("metrics.fresh") })
    await user.click(screen.getByRole("button", { name: /^Source:/ }))
    await user.click(await screen.findByRole("option", { name: "Source b" }))
    await waitFor(() => expect(router.state.location.search).toBe("?source=b"))
    await waitFor(() => expect(gateway.overview).toHaveBeenCalledWith({ sourceId: "b" }))
    expect(screen.getByRole("button", { name: "Source: Source b" })).toBeInTheDocument()
    await user.click(screen.getByRole("button", { name: /^Data type:/ }))
    await user.click(await screen.findByRole("option", { name: "Registry" }))
    await waitFor(() => expect(router.state.location.search).toContain("type=registry"))
    await user.click(screen.getByRole("button", { name: /^Company region:/ }))
    await user.type(screen.getByRole("combobox", { name: t("scope.searchRegion") }), "spb")
    await user.click(await screen.findByRole("option", { name: /Saint Petersburg/ }))
    await waitFor(() => expect(router.state.location.search).toContain("region=78"))
    await user.click(screen.getByRole("button", { name: t("scope.reset") }))
    await waitFor(() => expect(router.state.location.search).toBe(""))
  })

  it("distinguishes an empty base from an empty filter result", async () => {
    const none = overview({ offers: 0 })
    const gateway = stubAnalytics({ overview: vi.fn(async () => none) })
    renderAnalytics("/analytics", gateway)
    expect(await screen.findByText(t("state.empty"))).toBeInTheDocument()
    renderAnalytics("/analytics?region=99", gateway)
    expect(await screen.findByText(t("state.emptyFilter"))).toBeInTheDocument()
  })

  it("warns when the last recalculation failed and refreshes on request", async () => {
    const stale = overview({ meta: { ...meta, warnings: ["refresh_failed"] } })
    const gateway = stubAnalytics({ overview: vi.fn(async () => stale) })
    const { user } = renderAnalytics("/analytics", gateway)
    expect(await screen.findByText(t("snapshot.refreshFailed"))).toBeInTheDocument()
    const before = vi.mocked(gateway.overview).mock.calls.length
    await user.click(screen.getByRole("button", { name: t("snapshot.refresh") }))
    await waitFor(() =>
      expect(vi.mocked(gateway.overview).mock.calls.length).toBeGreaterThan(before),
    )
  })

  it("offers a retry when the data cannot be loaded", async () => {
    const gateway = stubAnalytics({
      overview: vi.fn(async () => {
        throw new ApiError({ status: 503, code: "analytics_unavailable" })
      }),
    })
    renderAnalytics("/analytics", gateway)
    expect(await screen.findByRole("button", { name: en("action.retry") })).toBeInTheDocument()
  })

  it("renders in Russian with the same figures", async () => {
    renderAnalytics(
      "/analytics",
      stubAnalytics({
        overview: vi.fn(async () => overview({ sources: [source("a")] })),
      }),
      "ru",
    )
    expect(
      await screen.findByRole("heading", { level: 1, name: "Аналитика" }),
    ).toBeInTheDocument()
  })
})
