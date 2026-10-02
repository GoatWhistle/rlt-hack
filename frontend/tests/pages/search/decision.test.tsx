import { cleanup, screen, waitFor, within } from "@testing-library/react"
import { en } from "@tests/support/dictionaries"
import { renderSearch } from "@tests/support/search"
import { afterEach, describe, expect, it, vi } from "vitest"
import { resetShortlists } from "@/entities/shortlist/store"
import { CSV_TYPE } from "@/features/export-results/csv"
import * as download from "@/shared/download/save-text-file"

const SEARCH = "1f0c3b5e-6a1d-4c2e-9f7a-2b8d4e6f1a90"
const EXPORT_FILE = "lotive-krupa-grechnevaya-yadritsa-2026-10-01.csv"
const NORTH = "6c1e2f3a-4b5c-4d6e-8f70-81a2b3c4d5e6"
const GRAIN = "7d2f3a4b-5c6d-4e7f-9081-92b3c4d5e6f7"

afterEach(() => {
  cleanup()
  localStorage.clear()
  resetShortlists()
  vi.restoreAllMocks()
  Object.assign(window, { matchMedia: undefined })
})

async function openResult(path = `/search/${SEARCH}`) {
  const view = renderSearch(path)
  await screen.findByRole("heading", { level: 1 })
  return view
}

function candidates() {
  return screen.getByRole("region", { name: en("candidates.title", "search") })
}

function resultHeader(): HTMLElement {
  return screen.getByRole("heading", { level: 1 }).closest("header") as HTMLElement
}

describe("deciding on a search result", () => {
  it("marks a chosen candidate and keeps the choice", async () => {
    const { user, unmount } = await openResult()
    const grounds = screen.getByRole("article", { name: /Северный Провиант/ })
    await user.click(
      within(grounds).getByRole("button", { name: en("panel.choose", "candidate") }),
    )
    expect(
      within(grounds).getByRole("button", { name: en("panel.chosen", "candidate") }),
    ).toBeVisible()
    const card = within(candidates()).getByRole("button", { name: /Северный Провиант/ })
    expect(within(card).getByText(en("card.chosen", "candidate"))).toBeVisible()
    unmount()
    await openResult()
    const again = within(candidates()).getByRole("button", { name: /Северный Провиант/ })
    expect(within(again).getByText(en("card.chosen", "candidate"))).toBeVisible()
  })

  it("downloads only the chosen candidates by default", async () => {
    const save = vi.spyOn(download, "saveTextFile").mockImplementation(() => {})
    const { user } = await openResult()
    await user.click(screen.getByRole("button", { name: /Зерновой Двор/ }))
    const grounds = screen.getByRole("article", { name: /Зерновой Двор/ })
    await user.click(
      within(grounds).getByRole("button", { name: en("panel.choose", "candidate") }),
    )
    const header = resultHeader()
    expect(header).toHaveTextContent("1 chosen")
    expect(header).toHaveTextContent(en("selection.pickMore", "candidate"))
    const compare = within(header).getByRole("button", { name: "Compare chosen: 1" })
    expect(compare).toHaveAttribute("aria-disabled", "true")
    expect(compare).toHaveAccessibleDescription(en("selection.compareHint", "candidate"))
    await user.click(compare)
    expect(screen.queryByRole("dialog")).toBeNull()
    expect(screen.queryByRole("region", { name: /chosen/i })).toBeNull()
    await user.click(
      within(header).getByRole("button", { name: en("header.export", "search") }),
    )
    const dialog = screen.getByRole("dialog", { name: en("search.title", "export") })
    expect(
      within(dialog).getByRole("radio", { name: "Only the ones you chose (1)" }),
    ).toBeChecked()
    expect(within(dialog).getByText("1 candidate is included.")).toBeInTheDocument()
    await user.click(
      within(dialog).getByRole("button", { name: en("search.submit", "export") }),
    )
    const [name, content, type] = save.mock.calls[0] ?? []
    expect(name).toBe(EXPORT_FILE)
    expect(type).toBe(CSV_TYPE)
    expect(content).toContain("АО «Зерновой Двор»")
    expect(content).not.toContain("Северный Провиант")
    expect(
      (await screen.findAllByText(`File downloaded: ${EXPORT_FILE}`)).length,
    ).toBeGreaterThan(0)
  })

  it("compares two chosen candidates and clears the choice", async () => {
    const { user } = await openResult()
    const choose = () =>
      user.click(screen.getByRole("button", { name: en("panel.choose", "candidate") }))
    await choose()
    await user.click(within(candidates()).getByRole("button", { name: /Зерновой Двор/ }))
    await choose()
    const exportButton = screen.getByRole("button", { name: en("header.export", "search") })
    expect(exportButton).toHaveTextContent("2")
    const header = resultHeader()
    expect(header).toHaveTextContent("2 chosen")
    await user.click(within(header).getByRole("button", { name: "Compare chosen: 2" }))
    const dialog = await screen.findByRole("dialog", { name: en("compare.title", "candidate") })
    const headers = within(within(dialog).getByRole("table")).getAllByRole("columnheader")
    expect(headers).toHaveLength(3)
    expect(headers[1]).toHaveTextContent("Северный Провиант")
    await user.click(within(dialog).getByRole("button", { name: en("action.close") }))
    await user.click(
      within(header).getByRole("button", { name: en("selection.clear", "candidate") }),
    )
    expect(screen.queryAllByText(en("card.chosen", "candidate"))).toHaveLength(0)
    await waitFor(() =>
      expect(within(header).queryByRole("button", { name: /Compare chosen/ })).toBeNull(),
    )
  })

  it("downloads everyone when nobody is chosen", async () => {
    const save = vi.spyOn(download, "saveTextFile").mockImplementation(() => {})
    const { user } = await openResult()
    await user.click(screen.getByRole("button", { name: en("header.export", "search") }))
    const dialog = screen.getByRole("dialog", { name: en("search.title", "export") })
    expect(
      within(dialog).getByRole("radio", { name: "Only the ones you chose (0)" }),
    ).toBeDisabled()
    await user.click(
      within(dialog).getByRole("button", { name: en("search.submit", "export") }),
    )
    const content = String(save.mock.calls[0]?.[1])
    expect(content).toContain("Северный Провиант")
    expect(content).toContain("Зерновой Двор")
    expect(content).toContain("search_id;rank;supplier_inn")
  })

  it("opens the candidate and item named in the address", async () => {
    const { user, router } = await openResult(`/search/${SEARCH}?candidate=${GRAIN}`)
    expect(screen.getByRole("article", { name: /Зерновой Двор/ })).toBeInTheDocument()
    await user.click(within(candidates()).getByRole("button", { name: /Северный Провиант/ }))
    expect(router.state.location.search).toBe(`?candidate=${NORTH}`)
    await user.click(screen.getByRole("button", { name: /Рис шлифованный/ }))
    expect(router.state.location.search).toBe(`?candidate=${NORTH}&item=i2`)
    const grounds = screen.getByRole("article", { name: /Северный Провиант/ })
    const focused = within(grounds).getByRole("article", { current: true })
    expect(focused).toHaveAccessibleName(/Рис шлифованный круглозёрный/)
  })

  it("lets the user decide right from the company profile", async () => {
    const { user } = await openResult()
    await user.click(screen.getByRole("button", { name: en("panel.profile", "candidate") }))
    const dialog = await screen.findByRole("dialog", { name: /Северный Провиант/ })
    await user.click(
      within(dialog).getByRole("button", { name: en("panel.choose", "candidate") }),
    )
    expect(
      within(dialog).getByRole("button", { name: en("panel.chosen", "candidate") }),
    ).toBeInTheDocument()
    expect(resultHeader()).toHaveTextContent("1 chosen")
  })

  it("names the region instead of its code", async () => {
    await openResult()
    const grounds = screen.getByRole("article", { name: /Северный Провиант/ })
    expect(within(grounds).getByText("Saint Petersburg (78)")).toBeInTheDocument()
  })
})

describe("deciding on a narrow screen", () => {
  it("moves the focus to the section that opens", async () => {
    Object.assign(window, {
      matchMedia: vi.fn(() => ({
        matches: true,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
      })),
      scrollBy: vi.fn(),
    })
    const { user } = await openResult(`/search/${SEARCH}?view=list`)
    await user.click(screen.getByRole("button", { name: /Рис шлифованный/ }))
    expect(
      screen.getByRole("heading", { level: 2, name: en("candidates.title", "search") }),
    ).toHaveFocus()
    await user.click(screen.getByRole("button", { name: /Северный Провиант/ }))
    expect(screen.getByRole("heading", { level: 2, name: /Северный Провиант/ })).toHaveFocus()
  })
})
