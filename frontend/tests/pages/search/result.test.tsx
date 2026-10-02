import { screen, waitFor, within } from "@testing-library/react"
import { en } from "@tests/support/dictionaries"
import { contractResult, renderSearch, stubSearch } from "@tests/support/search"
import { afterEach, describe, expect, it, vi } from "vitest"
import { ApiError } from "@/shared/api/api-error"
import { searchDraftPath } from "@/shared/config/paths"
import { NARROW_LAYOUT } from "@/shared/ui/workspace-layout"

afterEach(() => {
  Object.assign(window, { matchMedia: undefined })
})

function region(name: string) {
  return screen.getByRole("region", { name })
}

async function openContract() {
  const view = renderSearch("/search/1f0c")
  await screen.findByRole("heading", { level: 1 })
  return view
}

async function openVariant(
  change: (payload: Record<string, unknown>) => Record<string, unknown>,
) {
  const result = contractResult(change)
  const view = renderSearch(`/search/${result.searchId}`, {
    gateway: stubSearch({ get: vi.fn(async () => result) }),
  })
  await screen.findByRole("heading", { level: 1 })
  return view
}

describe("a search result", () => {
  it("shows the query, the items and the ranked candidates", async () => {
    await openContract()
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(
      "Крупа гречневая ядрица",
    )
    expect(screen.getByRole("textbox", { name: en("box.label", "search") })).toHaveValue(
      contractResult().query.text,
    )
    await waitFor(() => expect(document.title).toBe("lotive | Search"))
    const items = region(en("items.title", "search"))
    const groats = within(items).getByRole("button", { name: /Крупа гречневая ядрица/ })
    expect(groats).toHaveTextContent("500 кг")
    expect(groats).toHaveTextContent("1 candidate · +1 assumption")
    const candidates = region(en("candidates.title", "search"))
    const first = within(candidates).getByRole("button", { name: "ООО «Северный Провиант»" })
    expect(first).toHaveAttribute("aria-pressed", "true")
    expect(first).toHaveAccessibleDescription(/INN 7801234567/)
    expect(first).toHaveTextContent("2/2")
    expect(first).toHaveTextContent("11 similar · 4 wins")
    expect(within(first).queryByRole("meter")).toBeNull()
    expect(first).not.toHaveTextContent(/Covers/)
    const second = within(candidates).getByRole("button", { name: "АО «Зерновой Двор»" })
    expect(second).toHaveTextContent(en("noInn", "evidence"))
    expect(second).toHaveTextContent(`${en("reasonShort.innMissing", "candidate")} +3`)
  })

  it("grounds the chosen candidate in sources, history and contacts", async () => {
    const { user } = await openContract()
    const grounds = screen.getByRole("article", { name: /Северный Провиант/ })
    expect(within(grounds).getAllByText("2/2")).toHaveLength(2)
    expect(
      within(grounds).getByText(
        "Price list of Sep 29, 2026 for 1 item; won lot 32514850391-1.",
      ),
    ).toBeVisible()
    expect(
      within(grounds).getByRole("link", { name: "Прайс-лист компании (opens in a new tab)" }),
    ).toHaveAttribute("href", "https://severny-proviant.example.org/price/grechka")
    expect(within(grounds).getAllByText(/^checked Sep 29, 2026/).length).toBeGreaterThan(0)
    expect(within(grounds).getByText(en("basis.catalog", "evidence"))).toBeInTheDocument()
    expect(within(grounds).getByText("11 similar · wins: 4")).toBeInTheDocument()
    expect(within(grounds).getByText(/Lot 32514850391-1/)).toBeInTheDocument()
    expect(within(grounds).getByText("Items: Крупа гречневая ядрица")).toBeInTheDocument()
    expect(within(grounds).getByRole("link", { name: "+7 812 000-00-00" })).toHaveAttribute(
      "href",
      "tel:+78120000000",
    )
    await user.click(screen.getByRole("button", { name: /Зерновой Двор/ }))
    const check = screen.getByRole("article", { name: /Зерновой Двор/ })
    const reasons = within(check).getByRole("heading", {
      name: en("panel.checkTitle", "candidate"),
    }).parentElement as HTMLElement
    expect(
      within(reasons)
        .getAllByRole("listitem")
        .map((item) => item.querySelector("strong")?.textContent),
    ).toEqual([
      en("reasonShort.innMissing", "candidate"),
      en("reasonShort.roleUnconfirmed", "candidate"),
      en("reasonShort.noCurrentOffer", "candidate"),
      en("reasonShort.rangeUnconfirmed", "candidate"),
    ])
    expect(within(check).getByText(en("offer.inferred", "evidence"))).toBeVisible()
    await user.click(within(check).getByText(en("panel.companyTitle", "candidate")))
    expect(within(check).getByText(en("panel.noRoleBasis", "candidate"))).toBeVisible()
    expect(within(check).getByText(en("contacts.none", "evidence"))).toBeVisible()
  })

  it("shows who covers a chosen item and on what basis", async () => {
    const { user } = await openContract()
    const rice = within(region(en("items.title", "search"))).getByRole("button", {
      name: /Рис шлифованный/,
    })
    await user.click(rice)
    expect(rice).toHaveAttribute("aria-pressed", "true")
    const candidates = region(en("candidates.title", "search"))
    expect(within(candidates).getByText("Who covers “Рис шлифованный”")).toBeVisible()
    expect(within(candidates).queryByRole("button", { name: /Зерновой Двор/ })).toBeNull()
    const north = within(candidates).getByRole("button", { name: /Северный Провиант/ })
    expect(north).toHaveTextContent(`${en("basis.catalog", "evidence")} · Sep 28, 2026`)
    await user.click(
      within(candidates).getByRole("button", { name: en("list.reset", "candidate") }),
    )
    expect(within(candidates).getByRole("button", { name: /Зерновой Двор/ })).toBeVisible()
    await user.click(rice)
    await user.click(rice)
    expect(rice).toHaveAttribute("aria-pressed", "false")
  })

  it("narrows the candidates by their verdict from the address", async () => {
    const { user, router } = await openContract()
    const candidates = region(en("candidates.title", "search"))
    const verdicts = within(candidates).getByRole("group", {
      name: en("candidates.facets.legend", "search"),
    })
    expect(verdicts).toHaveTextContent("All2Recommended1To check1")
    await user.click(within(verdicts).getByRole("radio", { name: /^To check/ }))
    expect(router.state.location.search).toContain("status=check")
    expect(within(candidates).queryByRole("button", { name: /Северный Провиант/ })).toBeNull()
    expect(screen.getByRole("article", { name: /Зерновой Двор/ })).toBeInTheDocument()
  })

  it("starts a new search right from the result", async () => {
    const next = contractResult((payload) => ({ ...payload, searchId: "next-search" }))
    const search = vi.fn(async () => next)
    const { user, router } = renderSearch("/search/1f0c", {
      gateway: stubSearch({ search }),
    })
    const field = await screen.findByRole("textbox", { name: en("box.label", "search") })
    await user.clear(field)
    await user.type(field, "рис 200 кг")
    await user.click(screen.getByRole("button", { name: en("box.submit", "search") }))
    expect(search).toHaveBeenCalledWith({ text: "рис 200 кг", limit: 20 })
    await waitFor(() => expect(router.state.location.pathname).toBe("/search/next-search"))
  })

  it("warns quietly when the result may be incomplete", async () => {
    const { user } = await openVariant((payload) => {
      const [first, ...rest] = payload.items as Record<string, unknown>[]
      return {
        ...payload,
        items: [{ ...first, origin: "inferred" }, ...rest],
        warnings: [{ code: "itemsInferred", subject: "" }],
      }
    })
    expect(
      screen.getByRole("note", { name: en("warning.title", "candidate") }),
    ).toHaveTextContent(en("warning.itemsInferred", "candidate"))
    expect(screen.getByText(en("items.origin.inferred", "search"))).toBeVisible()
    await user.click(screen.getByRole("button", { name: /Зерновой Двор/ }))
    expect(screen.getByRole("article", { name: /Зерновой Двор/ })).toHaveTextContent(
      en("reasonText.rangeUnconfirmed", "candidate"),
    )
  })

  it("suggests one way forward when nobody matches", async () => {
    const { user } = await openVariant((payload) => ({
      ...payload,
      query: {
        ...(payload.query as Record<string, unknown>),
        text: "tractor tyres; engine oil",
      },
      candidates: [],
    }))
    expect(
      screen.getByRole("heading", { level: 2, name: en("empty.title", "search") }),
    ).toBeVisible()
    expect(screen.queryByRole("button", { pressed: false })).toBeNull()
    expect(screen.getAllByRole("button", { name: /Change the query/ })).toHaveLength(1)
    expect(
      screen.getByRole("link", { name: "Search only for “Рис шлифованный”" }),
    ).toHaveAttribute("href", searchDraftPath("Рис шлифованный"))
    expect(screen.getByRole("link", { name: en("empty.upload", "search") })).toHaveAttribute(
      "href",
      "/uploads",
    )
    await user.click(screen.getByRole("button", { name: /Change the query/ }))
    expect(screen.getByRole("textbox", { name: en("box.label", "search") })).toHaveFocus()
  })

  it("says when the search does not exist and retries other failures", async () => {
    const missing = vi.fn(async () => {
      throw new ApiError({ status: 404, code: "search_not_found" })
    })
    renderSearch("/search/gone", { gateway: stubSearch({ get: missing }) })
    expect(
      await screen.findByRole("heading", { level: 1, name: en("missing.title", "search") }),
    ).toBeVisible()
  })

  it("offers a retry when the search cannot be read", async () => {
    const get = vi.fn().mockRejectedValue(new ApiError({ status: 504, code: "search_timeout" }))
    const { user } = renderSearch("/search/slow", { gateway: stubSearch({ get }) })
    expect(await screen.findByText(en("search_timeout", "errors"))).toBeVisible()
    await user.click(screen.getByRole("button", { name: en("action.retry") }))
    expect(get.mock.calls.length).toBeGreaterThan(1)
  })
})

describe("a search result on a narrow screen", () => {
  it("shows one section at a time and moves to the grounds after a choice", async () => {
    const matchMedia = vi.fn(() => ({
      matches: true,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    }))
    Object.assign(window, { matchMedia, scrollBy: vi.fn() })
    const { user } = await openContract()
    expect(matchMedia).toHaveBeenCalledWith(NARROW_LAYOUT)
    expect(screen.getByRole("radio", { name: en("views.evidence", "search") })).toBeChecked()
    await user.click(screen.getByRole("radio", { name: en("views.items", "search") }))
    await user.click(screen.getByRole("button", { name: /Рис шлифованный/ }))
    expect(screen.getByRole("radio", { name: en("views.candidates", "search") })).toBeChecked()
    await user.click(screen.getByRole("button", { name: /Северный Провиант/ }))
    expect(screen.getByRole("radio", { name: en("views.evidence", "search") })).toBeChecked()
    const pager = screen.getByRole("navigation", { name: en("pager.label", "candidate") })
    expect(pager).toHaveTextContent("1 of 1")
    expect(
      within(pager).queryByRole("button", { name: en("pager.next", "candidate") }),
    ).toBeNull()
  })
})
