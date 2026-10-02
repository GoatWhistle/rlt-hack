import { screen, waitFor, within } from "@testing-library/react"
import { en } from "@tests/support/dictionaries"
import { lotSummary, renderPage, stubGateway, uploadDetail } from "@tests/support/gateway"
import { describe, expect, it, vi } from "vitest"
import { readLastUpload } from "@/entities/upload/last-upload"
import { PAGE_SIZE } from "@/entities/upload/list-query"
import { ApiError } from "@/shared/api/api-error"

function manyLots() {
  return Array.from({ length: PAGE_SIZE + 5 }, (_, index) =>
    lotSummary(String(100 + index), {
      title: index === 0 ? "Milk for schools" : `Purchase ${100 + index}`,
      status: index % 3 === 0 ? "needsCheck" : "ready",
    }),
  )
}

function gatewayWith(lots = manyLots(), overrides = {}) {
  return stubGateway({ get: vi.fn(async () => uploadDetail(lots, overrides)) })
}

describe("the purchases of a file", () => {
  it("shows the file, its finished processing and a dense table", async () => {
    renderPage("/uploads/u1", gatewayWith())
    expect(
      await screen.findByRole("heading", { level: 1, name: "notices.csv" }),
    ).toBeInTheDocument()
    expect(screen.getByText("Processing finished: 25 purchases")).toBeInTheDocument()
    const table = screen.getByRole("table", { name: "Purchases from notices.csv" })
    const headers = within(table)
      .getAllByRole("columnheader")
      .map((cell) => cell.textContent)
    expect(headers.slice(1)).toEqual([
      "Purchase",
      "Subject",
      "Status",
      "Published",
      "Start price",
      "Items",
      "Candidates",
    ])
    expect(within(table).getAllByRole("row")).toHaveLength(PAGE_SIZE + 1)
    const milk = within(table).getByRole("link", { name: "Milk for schools" })
    expect(milk).toHaveAttribute("href", "/uploads/u1/lots/100")
    expect(screen.getByText(`1–${PAGE_SIZE} of 25`)).toBeInTheDocument()
    expect(screen.getByRole("link", { name: "Page 1" })).toHaveAttribute("aria-current", "page")
    expect(screen.queryByRole("link", { name: en("pages.prev", "lots") })).toBeNull()
    const row = within(table).getByRole("row", { name: /Milk for schools/ })
    expect(row).toHaveTextContent("₽1,000 5 items 3 candidates")
    expect(readLastUpload()).toBe("u1")
  })

  it("searches and filters the whole file and keeps the query in the address", async () => {
    const { user, router } = renderPage("/uploads/u1", gatewayWith())
    await screen.findByRole("table")
    await user.click(screen.getByRole("link", { name: en("pages.next", "lots") }))
    expect(router.state.location.search).toBe("?page=2")
    expect(screen.getAllByRole("row")).toHaveLength(6)
    await user.click(screen.getByRole("radio", { name: /Need clarifying/ }))
    expect(router.state.location.search).toBe("?status=needsCheck")
    expect(
      screen.getByRole("radio", { name: /Need clarifying/ }).parentElement,
    ).toHaveTextContent("9")
    await user.type(screen.getByRole("searchbox", { name: en("search.label", "lots") }), "milk")
    expect(router.state.location.search).toBe("?q=milk&status=needsCheck")
    expect(screen.getByRole("link", { name: "Milk for schools" })).toHaveAttribute(
      "href",
      "/uploads/u1/lots/100?q=milk&status=needsCheck",
    )
    await user.type(screen.getByRole("searchbox"), "zzz")
    expect(
      screen.getByRole("heading", { name: "Nothing found for “milkzzz”" }),
    ).toBeInTheDocument()
    expect(
      screen.getByText(/Only purchases with the status “Need clarifying”/),
    ).toBeInTheDocument()
    await user.click(screen.getByRole("button", { name: en("empty.allStatuses", "lots") }))
    expect(router.state.location.search).toBe("?q=milkzzz")
    expect(screen.getByText(/Check the spelling/)).toBeInTheDocument()
    expect(screen.getByRole("link", { name: "Find suppliers for “milkzzz”" })).toHaveAttribute(
      "href",
      "/search?q=milkzzz",
    )
    await user.click(screen.getByRole("button", { name: en("empty.reset", "lots") }))
    expect(router.state.location.search).toBe("")
  })

  it("selects purchases and offers to download the selection", async () => {
    const { user } = renderPage("/uploads/u1", gatewayWith())
    await screen.findByRole("table")
    await user.click(screen.getByRole("checkbox", { name: "Select lot 100" }))
    const pageBox = screen.getByRole("checkbox", { name: en("table.selectPage", "lots") })
    expect(pageBox).toHaveProperty("indeterminate", true)
    const bar = screen.getByRole("region", { name: en("selection.label", "lots") })
    expect(within(bar).getByText("1 purchase selected")).toBeInTheDocument()
    await user.click(pageBox)
    expect(within(bar).getByText(`${PAGE_SIZE} purchases selected`)).toBeInTheDocument()
    await user.click(within(bar).getByRole("button", { name: en("selection.export", "lots") }))
    const dialog = await screen.findByRole("dialog", { name: en("title", "export") })
    expect(within(dialog).getByRole("radio", { name: `Selected (${PAGE_SIZE})` })).toBeChecked()
    await user.click(within(dialog).getByRole("button", { name: en("action.close") }))
    await user.click(pageBox)
    await waitFor(() =>
      expect(screen.queryByRole("region", { name: en("selection.label", "lots") })).toBeNull(),
    )
  })

  it("clears the selection on request and opens the full export from the header", async () => {
    const { user } = renderPage("/uploads/u1", gatewayWith())
    await screen.findByRole("table")
    await user.click(screen.getByRole("checkbox", { name: "Select lot 100" }))
    await user.click(screen.getByRole("button", { name: en("selection.clear", "lots") }))
    expect(screen.getByRole("checkbox", { name: en("table.selectPage", "lots") })).toHaveFocus()
    await waitFor(() =>
      expect(screen.queryByRole("region", { name: en("selection.label", "lots") })).toBeNull(),
    )
    await user.click(screen.getByRole("button", { name: en("download", "lots") }))
    const dialog = await screen.findByRole("dialog")
    expect(
      within(dialog).getByRole("radio", { name: "All purchases in the file (25)" }),
    ).toBeChecked()
  })

  it("shows running processing, queued rows and skipped rows separately", async () => {
    const lots = [
      lotSummary("1"),
      lotSummary("2", { status: "queued", startPrice: undefined, customerInn: undefined }),
    ]
    const { user } = renderPage(
      "/uploads/u1",
      gatewayWith(lots, {
        processed: 1,
        rejected: 1,
        issues: [{ row: 7, code: "missingTitle" }],
      }),
    )
    expect(await screen.findAllByText("Processing: 1 of 2 ready")).toHaveLength(2)
    expect(screen.getByRole("status")).toHaveTextContent("Processing: 1 of 2 ready")
    expect(screen.getByText(en("processing.hint", "lots"))).toBeInTheDocument()
    const queued = screen.getByRole("row", { name: /Purchase 2/ })
    expect(within(queued).getByText(en("status.queued", "lots"))).toBeInTheDocument()
    expect(within(queued).getByText(en("table.noPrice", "lots"))).toBeInTheDocument()
    expect(within(queued).getByText(/customer not given/i)).toBeInTheDocument()
    expect(within(queued).getByText(en("table.priceMissing", "lots"))).toBeInTheDocument()
    await user.click(screen.getByText("1 row was not processed because of errors"))
    expect(screen.getByText("Row 7")).toBeVisible()
  })

  it("marks lots that could not be processed and filters them only when there are any", async () => {
    const first = renderPage("/uploads/u1", gatewayWith())
    await screen.findByRole("table")
    expect(screen.queryByRole("radio", { name: /Not processed/ })).toBeNull()
    first.unmount()
    const lots = [lotSummary("1"), lotSummary("2", { status: "failed", products: 0 })]
    const view = renderPage("/uploads/u1", gatewayWith(lots))
    await screen.findByRole("table")
    const failed = screen.getByRole("row", { name: /Purchase 2/ })
    expect(within(failed).getByText(en("status.failed", "lots"))).toBeInTheDocument()
    expect(within(failed).getAllByText(en("table.pending", "lots"))).toHaveLength(3)
    await view.user.click(screen.getByRole("radio", { name: /Not processed/ }))
    expect(view.router.state.location.search).toBe("?status=failed")
    expect(screen.getAllByRole("row")).toHaveLength(2)
  })

  it("explains a missing upload and other failures", async () => {
    renderPage(
      "/uploads/x",
      stubGateway({
        get: vi.fn(async () => Promise.reject(new ApiError({ status: 404, code: "notFound" }))),
      }),
    )
    expect(
      await screen.findByRole("heading", { name: en("missing.title", "lots") }),
    ).toBeInTheDocument()
    expect(screen.getByRole("link", { name: en("missing.action", "lots") })).toHaveAttribute(
      "href",
      "/history?tab=files",
    )
  })

  it("offers a retry when the file cannot load", async () => {
    renderPage(
      "/uploads/x",
      stubGateway({
        get: vi.fn(async () => Promise.reject(new ApiError({ status: 500, code: "server" }))),
      }),
    )
    await waitFor(
      () =>
        expect(screen.getByRole("button", { name: en("action.retry") })).toBeInTheDocument(),
      {
        timeout: 6000,
      },
    )
  })
})
