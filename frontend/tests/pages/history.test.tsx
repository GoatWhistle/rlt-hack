import { screen, within } from "@testing-library/react"
import { en } from "@tests/support/dictionaries"
import { renderPage, stubGateway, uploadSummary } from "@tests/support/gateway"
import { afterEach, describe, expect, it, vi } from "vitest"
import type { UploadSummary } from "@/entities/upload/model"
import { WIDE_HISTORY } from "@/pages/history"
import { kindOf } from "@/pages/history/history-row"

const now = new Date().toISOString()
const query = uploadSummary({
  id: "q1",
  fileName: "search.csv",
  title: "Office paper A4",
  total: 1,
  processed: 1,
  createdAt: now,
  counts: { ready: 1, needsCheck: 0, noCandidates: 0, failed: 0 },
})
const empty = uploadSummary({
  id: "q2",
  fileName: "search.csv",
  title: "Tractor",
  total: 1,
  processed: 1,
  createdAt: now,
  counts: { ready: 0, needsCheck: 0, noCandidates: 1, failed: 0 },
})
const file = uploadSummary({
  id: "f1",
  fileName: "notices.xlsx",
  total: 18,
  processed: 18,
  createdAt: now,
  counts: { ready: 15, needsCheck: 0, noCandidates: 3, failed: 0 },
})
const working = uploadSummary({
  id: "f2",
  fileName: "spec.pdf",
  total: 4,
  processed: 1,
  createdAt: now,
})

function wide(matches: boolean) {
  vi.stubGlobal("matchMedia", (media: string) => ({
    matches: matches && media === WIDE_HISTORY,
    media,
    addEventListener: () => undefined,
    removeEventListener: () => undefined,
  }))
}

function show(uploads: UploadSummary[], path = "/history") {
  return renderPage(path, stubGateway({ list: vi.fn(async () => uploads) }))
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe("the history page", () => {
  it("splits text queries and files into two columns on a wide screen", async () => {
    wide(true)
    show([query, empty, file, working])
    const queries = await screen.findByRole("region", { name: en("queries.title", "history") })
    const files = screen.getByRole("region", { name: en("files.title", "history") })
    expect(
      await within(queries).findByRole("link", { name: /Office paper A4/ }),
    ).toHaveAttribute("href", "/uploads/q1/lots/query")
    expect(within(queries).getByText(en("row.found", "history"))).toBeVisible()
    expect(within(queries).getByText(en("row.notFound", "history"))).toBeVisible()
    const upload = within(files).getByRole("link", { name: /notices\.xlsx/ })
    expect(upload).toHaveAttribute("href", "/uploads/f1")
    expect(upload).toHaveTextContent("18 purchases")
    expect(upload).toHaveTextContent("3 without candidates")
    expect(within(files).getByRole("progressbar")).toBeInTheDocument()
    expect(within(queries).getAllByRole("heading", { level: 3 })[0]).toHaveTextContent("Today")
    expect(screen.queryByRole("group", { name: en("tabs.legend", "history") })).toBeNull()
  })

  it("switches between queries and files on a narrow screen and keeps the choice", async () => {
    wide(false)
    const { user, router } = show([query, file])
    expect(await screen.findByRole("link", { name: /Office paper A4/ })).toBeVisible()
    expect(screen.queryByRole("link", { name: /notices\.xlsx/ })).toBeNull()
    await user.click(screen.getByRole("radio", { name: /Files/ }))
    expect(screen.getByRole("link", { name: /notices\.xlsx/ })).toBeVisible()
    expect(router.state.location.search).toBe("?tab=files")
  })

  it("filters both columns and explains an empty match", async () => {
    wide(true)
    const { user } = show([query, file])
    const filter = await screen.findByRole("searchbox", { name: en("filter.label", "history") })
    await user.type(filter, "notices")
    expect(screen.queryByRole("link", { name: /Office paper/ })).toBeNull()
    expect(screen.getByRole("link", { name: /notices\.xlsx/ })).toBeVisible()
    await user.clear(filter)
    await user.type(filter, "zzz")
    const resets = screen.getAllByRole("button", { name: en("reset", "history") })
    expect(resets).toHaveLength(2)
    await user.click(resets[0] as HTMLElement)
    expect(filter).toHaveValue("")
  })

  it("teaches what each column will hold when the history is empty", async () => {
    wide(true)
    show([])
    expect(await screen.findByText(en("queries.empty", "history"))).toBeVisible()
    expect(screen.getByText(en("files.empty", "history"))).toBeVisible()
    expect(screen.getByRole("link", { name: en("files.start", "history") })).toHaveAttribute(
      "href",
      "/search",
    )
  })

  it("shows more rows on demand", async () => {
    wide(true)
    const many = Array.from({ length: 23 }, (_, index) =>
      uploadSummary({ id: `f${index}`, fileName: `batch-${index}.csv`, createdAt: now }),
    )
    const { user } = show(many)
    const more = await screen.findByRole("button", { name: "Show 3 more" })
    expect(screen.getAllByRole("link", { name: /batch-/ })).toHaveLength(20)
    await user.click(more)
    expect(screen.getAllByRole("link", { name: /batch-/ })).toHaveLength(23)
  })

  it("names the type of each file", () => {
    expect(kindOf("a.CSV")).toBe("csv")
    expect(kindOf("a.xls")).toBe("xlsx")
    expect(kindOf("a.pdf")).toBe("pdf")
    expect(kindOf("a.doc")).toBe("docx")
    expect(kindOf("archive")).toBe("other")
  })

  it("offers to retry when the history fails to load", async () => {
    wide(true)
    renderPage(
      "/history",
      stubGateway({
        list: vi.fn(async () => {
          throw new Error("down")
        }),
      }),
    )
    expect(await screen.findAllByRole("button", { name: en("action.retry") })).toHaveLength(2)
    expect(screen.getAllByRole("alert")).toHaveLength(2)
  })

  it("keeps both columns in place while the history loads", () => {
    wide(true)
    renderPage(
      "/history",
      stubGateway({ list: vi.fn(() => new Promise<never>(() => undefined)) }),
    )
    expect(screen.getByRole("region", { name: en("queries.title", "history") })).toBeVisible()
    expect(screen.getByRole("region", { name: en("files.title", "history") })).toBeVisible()
    expect(screen.getAllByRole("status")).not.toHaveLength(0)
  })
})
