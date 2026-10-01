import { act, screen, waitFor } from "@testing-library/react"
import { en } from "@tests/support/dictionaries"
import { lotSummary, renderPage, stubGateway, uploadDetail } from "@tests/support/gateway"
import { describe, expect, it, vi } from "vitest"
import { PAGE_SIZE } from "@/entities/upload/list-query"
import { pageItems } from "@/pages/lots/pagination"

function gatewayWith(count = PAGE_SIZE + 5) {
  const lots = Array.from({ length: count }, (_, index) => lotSummary(String(100 + index)))
  return stubGateway({ get: vi.fn(async () => uploadDetail(lots)) })
}

describe("the purchases list controls", () => {
  it("shows skeleton rows while the file loads", async () => {
    renderPage("/uploads/u1", stubGateway({ get: vi.fn(() => new Promise<never>(() => {})) }))
    const status = await screen.findByRole("status")
    expect(status).toHaveAttribute("aria-busy", "true")
    expect(status).toHaveTextContent(en("loading", "lots"))
  })

  it("clears the search with a button or Escape and focuses it with a slash", async () => {
    const { user, router } = renderPage("/uploads/u1", gatewayWith())
    const search = await screen.findByRole("searchbox", { name: en("search.label", "lots") })
    expect(search).toHaveAttribute("aria-keyshortcuts", "/")
    await user.type(search, "101")
    expect(router.state.location.search).toBe("?q=101")
    await user.click(screen.getByRole("button", { name: en("search.clear", "lots") }))
    expect(router.state.location.search).toBe("")
    expect(search).toHaveFocus()
    await user.type(search, "10{Escape}")
    expect(router.state.location.search).toBe("")
    search.blur()
    await user.keyboard("/")
    expect(search).toHaveFocus()
    expect(search).toHaveValue("")
    await user.keyboard("/")
    expect(search).toHaveValue("/")
  })

  it("ignores the slash with modifiers or inside other fields", async () => {
    const { user } = renderPage("/uploads/u1", gatewayWith())
    const search = await screen.findByRole("searchbox")
    await user.keyboard("{Control>}/{/Control}")
    expect(search).not.toHaveFocus()
    const box = screen.getByRole("checkbox", { name: "Select lot 100" })
    box.focus()
    await user.keyboard("/")
    expect(box).toHaveFocus()
  })

  it("moves between pages with a clear current page and no dead links", async () => {
    const { user, router } = renderPage("/uploads/u1", gatewayWith())
    await screen.findByRole("table")
    await user.click(screen.getByRole("link", { name: "Page 2" }))
    expect(router.state.location.search).toBe("?page=2")
    expect(screen.getByRole("link", { name: "Page 2" })).toHaveAttribute("aria-current", "page")
    expect(screen.queryByRole("link", { name: en("pages.next", "lots") })).toBeNull()
    await user.click(screen.getByRole("link", { name: en("pages.prev", "lots") }))
    expect(router.state.location.search).toBe("")
  })

  it("forgets the selection when another file opens", async () => {
    const { user, router } = renderPage("/uploads/u1", gatewayWith())
    await user.click(await screen.findByRole("checkbox", { name: "Select lot 100" }))
    expect(screen.getByRole("region", { name: en("selection.label", "lots") })).toBeVisible()
    await act(() => router.navigate("/uploads/u2"))
    await waitFor(() =>
      expect(screen.queryByRole("region", { name: en("selection.label", "lots") })).toBeNull(),
    )
    expect(screen.getByRole("checkbox", { name: "Select lot 100" })).not.toBeChecked()
  })
})

describe("the page numbers", () => {
  it("lists every page of a short file", () => {
    expect(pageItems(1, 3)).toEqual([1, 2, 3])
  })

  it("keeps the ends and the neighbours of the current page", () => {
    expect(pageItems(5, 10)).toEqual([1, -4, 4, 5, 6, -10, 10])
    expect(pageItems(1, 10)).toEqual([1, 2, -10, 10])
    expect(pageItems(10, 10)).toEqual([1, -9, 9, 10])
  })
})
