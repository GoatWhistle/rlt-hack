import { screen, waitFor } from "@testing-library/react"
import { renderAnalytics, stubAnalytics } from "@tests/support/analytics"
import { en } from "@tests/support/dictionaries"
import { describe, expect, it, vi } from "vitest"
import { ApiError } from "@/shared/api/api-error"

const t = (path: string) => en(path, "analytics")

describe("the records behind a figure", () => {
  it("asks for the problem, category and page named in the address", async () => {
    const gateway = stubAnalytics()
    renderAnalytics("/analytics/records?problem=stale&category=01.11&page=2&source=a", gateway)
    expect(await screen.findByRole("link", { name: "Offer one" })).toHaveAttribute(
      "href",
      "https://example.org/1",
    )
    expect(gateway.records).toHaveBeenCalledWith(
      { sourceId: "a" },
      { problem: "stale", category: "01.11", offset: 25, limit: 25 },
    )
    expect(screen.getByText("Showing: Overdue, category 01.11")).toBeInTheDocument()
    expect(screen.getByText("26–30 of 30")).toBeInTheDocument()
    expect(screen.getByRole("link", { name: t("records.previous") })).toHaveAttribute(
      "href",
      "/analytics/records?problem=stale&category=01.11&source=a",
    )
    expect(screen.queryByRole("link", { name: t("records.next") })).toBeNull()
    expect(screen.getByRole("status")).toHaveTextContent("2 records changed")
  })

  it("moves to the next page", async () => {
    const { user, router } = renderAnalytics("/analytics/records", stubAnalytics())
    await user.click(await screen.findByRole("link", { name: t("records.next") }))
    await waitFor(() => expect(router.state.location.search).toBe("?page=2"))
  })

  it("shows placeholders for missing values and an empty result", async () => {
    renderAnalytics("/analytics/records", stubAnalytics())
    await screen.findByRole("link", { name: "Offer two" })
    expect(screen.getAllByText(t("records.noValue")).length).toBeGreaterThan(2)
    const none = vi.fn(async () => ({
      asOf: "2026-10-02T09:00:00Z",
      total: 0,
      changedAfter: 0,
      items: [],
    }))
    renderAnalytics("/analytics/records", stubAnalytics({ records: none }))
    expect(await screen.findByText(t("records.empty"))).toBeInTheDocument()
  })

  it("reports a failure", async () => {
    const broken = vi.fn(async () => {
      throw new ApiError({ status: 500, code: "internal" })
    })
    renderAnalytics("/analytics/records", stubAnalytics({ records: broken }))
    expect(await screen.findAllByRole("button", { name: en("action.retry") })).not.toHaveLength(
      0,
    )
  })
})
