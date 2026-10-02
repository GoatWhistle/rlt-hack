import { screen, within } from "@testing-library/react"
import { en } from "@tests/support/dictionaries"
import { contractResult, renderSearch, stubSearch } from "@tests/support/search"
import { afterEach, describe, expect, it, vi } from "vitest"
import { ApiError } from "@/shared/api/api-error"
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
    const items = region(en("items.title", "search"))
    expect(
      within(items).getByRole("button", { name: /Крупа гречневая ядрица/ }),
    ).toHaveTextContent("500 кг")
    const candidates = region(en("candidates.title", "search"))
    const first = within(candidates).getByRole("button", { name: /Северный Провиант/ })
    expect(first).toHaveAttribute("aria-pressed", "true")
    expect(first).toHaveTextContent("INN 7801234567")
    expect(first).toHaveTextContent("Covers 2 of 2 items · In stock for 1 item")
    expect(within(first).getByRole("meter", { name: "Relevance" })).toHaveAttribute(
      "aria-valuetext",
      "0.82 out of 1",
    )
    const second = within(candidates).getByRole("button", { name: /Зерновой Двор/ })
    expect(second).toHaveTextContent(en("noInn", "evidence"))
    expect(second).toHaveTextContent(en("status.check", "evidence"))
  })

  it("grounds the chosen candidate in sources, history and contacts", async () => {
    const { user } = await openContract()
    const grounds = screen.getByRole("article", { name: /Северный Провиант/ })
    expect(within(grounds).getAllByText("2/2")).toHaveLength(2)
    expect(
      within(grounds).getByRole("link", { name: "Прайс-лист компании (opens in a new tab)" }),
    ).toHaveAttribute("href", "https://severny-proviant.example.org/price/grechka")
    expect(within(grounds).getByText("checked Sep 29, 2026")).toBeInTheDocument()
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
    expect(check).toHaveTextContent(en("checkReason.innMissing", "evidence"))
    expect(within(check).getByText(en("evidence.noRoleBasis", "search"))).toBeVisible()
    expect(within(check).getByText(en("contacts.none", "evidence"))).toBeVisible()
    expect(within(check).getByText(en("noSource", "evidence"))).toBeVisible()
  })

  it("keeps only the candidates that cover a chosen item", async () => {
    const { user } = await openContract()
    const rice = within(region(en("items.title", "search"))).getByRole("button", {
      name: /Рис шлифованный/,
    })
    await user.click(rice)
    expect(rice).toHaveAttribute("aria-pressed", "true")
    const candidates = region(en("candidates.title", "search"))
    expect(within(candidates).getByText("Candidates for “Рис шлифованный”")).toBeVisible()
    expect(within(candidates).queryByRole("button", { name: /Зерновой Двор/ })).toBeNull()
    await user.click(within(candidates).getByRole("button", { name: "Reset" }))
    expect(within(candidates).getByRole("button", { name: /Зерновой Двор/ })).toBeVisible()
    await user.click(rice)
    await user.click(rice)
    expect(rice).toHaveAttribute("aria-pressed", "false")
  })

  it("warns quietly when the result may be incomplete and shows more on request", async () => {
    const { user } = await openVariant((payload) => {
      const [first, ...rest] = payload.items as Record<string, unknown>[]
      return {
        ...payload,
        items: [{ ...first, origin: "inferred" }, ...rest],
        warnings: [{ code: "itemsInferred", subject: "" }],
      }
    })
    expect(screen.getByRole("note", { name: en("warning.title", "search") })).toHaveTextContent(
      en("warning.itemsInferred", "search"),
    )
    expect(screen.getByText(en("items.origin.inferred", "search"))).toBeVisible()
    await user.click(screen.getByRole("button", { name: /Зерновой Двор/ }))
    expect(screen.getByRole("article", { name: /Зерновой Двор/ })).toHaveTextContent(
      en("checkReason.rangeUnconfirmed", "evidence"),
    )
  })

  it("suggests rephrasing when nobody matches", async () => {
    await openVariant((payload) => ({
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
    const links = screen.getAllByRole("link", { name: en("empty.action", "search") })
    for (const link of links) {
      expect(link).toHaveAttribute("href", "/search?q=tractor+tyres%3B+engine+oil")
    }
  })

  it("opens the company profile with current offers", async () => {
    const { user } = await openContract()
    await user.click(screen.getByRole("button", { name: en("evidence.profile", "search") }))
    const dialog = await screen.findByRole("dialog", { name: "ООО «Северный Провиант»" })
    expect(
      await within(dialog).findByText("Крупа гречневая ядрица 1 сорт, мешок 50 кг"),
    ).toBeVisible()
    expect(within(dialog).getByText("RUB 84.50 per кг")).toBeVisible()
    expect(within(dialog).getByText(en("availability.available", "supplier"))).toBeVisible()
    expect(within(dialog).getByText(en("identity.verified", "supplier"))).toBeVisible()
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
  })
})
