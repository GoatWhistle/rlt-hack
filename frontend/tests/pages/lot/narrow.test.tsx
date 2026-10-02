import { screen, within } from "@testing-library/react"
import { en } from "@tests/support/dictionaries"
import { afterEach, describe, expect, it, vi } from "vitest"
import { resetShortlists } from "@/entities/shortlist/store"
import { NARROW_LAYOUT } from "@/pages/lot/workspace"
import { LONG_NAME } from "../../entities/recommendation/fixture"
import { openLot } from "./open-lot"

afterEach(() => {
  resetShortlists()
  Object.assign(window, { matchMedia: undefined })
})

describe("on a narrow screen", () => {
  it("shows one section at a time and moves to the grounds after a choice", async () => {
    const matchMedia = vi.fn((query: string) => ({
      matches: query === NARROW_LAYOUT,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    }))
    Object.assign(window, { matchMedia })
    const scrollBy = vi.fn()
    Object.assign(window, { scrollBy })
    const { user } = await openLot()
    expect(matchMedia).toHaveBeenCalledWith(NARROW_LAYOUT)
    expect(screen.getByRole("radio", { name: en("views.evidence", "lot") })).toBeChecked()
    expect(screen.queryByRole("region", { name: en("products.title", "lot") })).toBeNull()
    const stack = screen.getByRole("group", { name: en("views.legend", "lot") }).parentElement
      ?.parentElement as HTMLElement
    vi.spyOn(stack, "getBoundingClientRect").mockReturnValue({ top: -120 } as DOMRect)
    await user.click(screen.getByRole("radio", { name: en("views.products", "lot") }))
    expect(scrollBy).toHaveBeenCalledWith({ top: -120 })
    expect(screen.getByRole("radio", { name: en("views.products", "lot") })).toHaveFocus()
    await user.click(screen.getByRole("button", { name: "Show candidates with “Tea”" }))
    expect(screen.getByRole("radio", { name: en("views.companies", "lot") })).toBeChecked()
    expect(
      screen.getByRole("heading", { level: 2, name: en("companies.title", "lot") }),
    ).toHaveFocus()
    await user.click(screen.getByRole("button", { name: LONG_NAME }))
    expect(screen.getByRole("article", { name: LONG_NAME })).toBeInTheDocument()
    expect(screen.getByRole("heading", { level: 2, name: LONG_NAME })).toHaveFocus()
  })

  it("steps to the next candidate right from the grounds", async () => {
    Object.assign(window, {
      matchMedia: (query: string) => ({
        matches: query === NARROW_LAYOUT,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
      }),
    })
    const { user } = await openLot()
    const pager = screen.getByRole("navigation", { name: en("pager.label", "candidate") })
    expect(pager).toHaveTextContent("1 of 3")
    await user.click(within(pager).getByRole("button", { name: en("pager.next", "candidate") }))
    expect(screen.getByRole("article", { name: LONG_NAME })).toBeInTheDocument()
    expect(
      screen.getByRole("navigation", { name: en("pager.label", "candidate") }),
    ).toHaveTextContent("2 of 3")
    await user.click(screen.getByRole("button", { name: en("pager.prev", "candidate") }))
    expect(screen.getByRole("article", { name: "North Foods" })).toBeInTheDocument()
  })
})
