import { screen, waitFor, within } from "@testing-library/react"
import { en } from "@tests/support/dictionaries"
import { stubGateway, uploadSummary } from "@tests/support/gateway"
import { renderSearch } from "@tests/support/search"
import { describe, expect, it, vi } from "vitest"
import { foundPath } from "@/pages/search/home"
import { latestOf } from "@/pages/search/latest-strip"

function strip() {
  return screen.findByRole("navigation", { name: en("latest.label", "search") })
}

describe("the search page", () => {
  it("invites a description and shows no recent strip without history", async () => {
    const uploads = stubGateway()
    renderSearch("/search", { uploads })
    expect(
      screen.getByRole("heading", { level: 1, name: en("home.title", "search") }),
    ).toBeInTheDocument()
    await waitFor(() => expect(uploads.list).toHaveBeenCalled())
    expect(screen.queryByRole("navigation", { name: en("latest.label", "search") })).toBeNull()
    expect(screen.queryByRole("region", { name: /recent searches/i })).toBeNull()
    expect(screen.getByText(/CSV, XLSX, PDF, DOCX/)).toBeInTheDocument()
  })

  it("links the latest searches and files and the whole history", async () => {
    const list = vi.fn(async () => [
      uploadSummary({ id: "old", fileName: "old.csv", createdAt: "2026-09-01T10:00:00Z" }),
      uploadSummary({
        id: "text",
        fileName: "search.csv",
        title: "Buckwheat 500 kg",
        total: 1,
        processed: 1,
        createdAt: "2026-10-02T10:00:00Z",
      }),
      uploadSummary({ id: "file", fileName: "notices.csv", createdAt: "2026-10-01T10:00:00Z" }),
      uploadSummary({
        id: "plain",
        fileName: "search.csv",
        title: "",
        total: 1,
        processed: 1,
        createdAt: "2026-09-30T10:00:00Z",
      }),
    ])
    renderSearch("/search", { uploads: stubGateway({ list }) })
    const nav = await strip()
    const links = within(nav).getAllByRole("link")
    expect(links.map((link) => link.getAttribute("href"))).toEqual([
      "/uploads/text/lots/query",
      "/uploads/file",
      "/uploads/plain/lots/query",
      "/uploads/old",
      "/history",
    ])
    expect(links[0]).toHaveTextContent("Buckwheat 500 kg")
    expect(links[1]).toHaveTextContent("notices.csv")
    expect(links[2]).toHaveTextContent("search.csv")
    expect(links[4]).toHaveTextContent(en("latest.all", "search"))
    expect(nav).toHaveTextContent(en("latest.title", "search"))
  })

  it("keeps only the newest uploads for the strip", () => {
    const at = (id: string, day: number) =>
      uploadSummary({ id, createdAt: `2026-10-0${day}T10:00:00Z` })
    const all = [1, 4, 2, 3, 6, 5].map((day) => at(`d${day}`, day))
    expect(latestOf(all).map((u) => u.id)).toEqual(["d6", "d5", "d4", "d3", "d2"])
  })

  it("opens one purchase directly and a file with several on its upload page", () => {
    const result = uploadSummary({ id: "u9" })
    expect(foundPath(result, ["query"])).toBe("/uploads/u9/lots/query")
    expect(foundPath(result, ["1", "2"])).toBe("/uploads/u9")
    expect(foundPath(result, [])).toBe("/uploads/u9")
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

  it("offers example queries that fill the description", async () => {
    const { user } = renderSearch("/search")
    const ideas = screen.getByRole("region", { name: en("ideas.title", "search") })
    const paper = en("ideas.items.paper", "search")
    await user.click(within(ideas).getByRole("link", { name: paper }))
    expect(await screen.findByRole("textbox", { name: en("box.label", "search") })).toHaveValue(
      paper,
    )
  })
})
