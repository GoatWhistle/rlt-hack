import { screen, waitFor, within } from "@testing-library/react"
import { en } from "@tests/support/dictionaries"
import { lotSummary, renderPage, uploadDetail } from "@tests/support/gateway"
import { afterEach, describe, expect, it, vi } from "vitest"
import type { LotDetail } from "@/entities/upload/model"
import { LONG_NAME } from "../../entities/recommendation/fixture"
import { LOTS, lotDetail, lotGateway, openLot, panel } from "./open-lot"

afterEach(() => {
  vi.useRealTimers()
})

function pressed() {
  const companies = screen.getByRole("region", { name: en("companies.title", "lot") })
  return within(companies).getByRole("button", { pressed: true })
}

describe("the review address", () => {
  it("keeps the chosen candidate and product filter in the address", async () => {
    const { user, router } = await openLot(undefined, {
      path: "/uploads/u1/lots/10?status=ready",
    })
    await user.click(screen.getByRole("button", { name: /West Trade/ }))
    expect(router.state.location.search).toBe("?status=ready&company=west")
    await user.click(screen.getByRole("button", { name: "Show candidates with “Rice”" }))
    expect(router.state.location.search).toBe("?status=ready&company=west&product=rice")
    expect(await screen.findByRole("link", { name: en("header.next", "lot") })).toHaveAttribute(
      "href",
      "/uploads/u1/lots/11?status=ready",
    )
  })

  it("opens the candidate named in the address", async () => {
    await openLot(undefined, { path: "/uploads/u1/lots/10?company=west" })
    expect(pressed()).toHaveAccessibleName(/West Trade/)
    expect(panel("West Trade")).toBeInTheDocument()
  })

  it("falls back to the first candidate for an unknown one", async () => {
    await openLot(undefined, { path: "/uploads/u1/lots/10?company=ghost&product=ghost" })
    expect(pressed()).toHaveAccessibleName(/North Foods/)
  })
})

describe("walking between purchases", () => {
  it("keeps the header and the focus while the next purchase loads", async () => {
    let finish: (detail: LotDetail) => void = () => undefined
    const lot = vi.fn(async (_upload: string, lotId: string) =>
      lotId === "10"
        ? lotDetail()
        : new Promise<LotDetail>((resolve) => {
            finish = resolve
          }),
    )
    const gateway = lotGateway(lotDetail(), {
      lot,
      get: vi.fn(async () => uploadDetail([...LOTS, lotSummary("12")])),
    })
    const view = renderPage("/uploads/u1/lots/10", gateway)
    await view.findByRole("heading", { level: 1, name: "Food supply" })
    const next = await screen.findByRole("link", { name: en("header.next", "lot") })
    await view.user.click(next)
    expect(
      await screen.findByRole("heading", { level: 1, name: "Purchase 11" }),
    ).toBeInTheDocument()
    expect(next).toHaveFocus()
    const body = screen.getByRole("article", { name: "North Foods" }).closest("[aria-busy]")
    expect(body).toHaveAttribute("aria-busy", "true")
    finish(lotDetail({ lot: LOTS[2] }))
    await waitFor(() => expect(body).toHaveAttribute("aria-busy", "false"))
    expect(next).toHaveFocus()
  })

  it("moves with the bracket keys outside text fields", async () => {
    const lot = vi.fn(async (_upload: string, lotId: string) =>
      lotDetail({ lot: LOTS.find((item) => item.id === lotId) }),
    )
    const { user, router } = renderPage("/uploads/u1/lots/10", lotGateway(lotDetail(), { lot }))
    await screen.findByRole("link", { name: en("header.next", "lot") })
    await user.keyboard("]")
    await waitFor(() => expect(router.state.location.pathname).toBe("/uploads/u1/lots/11"))
    await screen.findByRole("link", { name: en("header.prev", "lot") })
    await user.keyboard("[[")
    await waitFor(() => expect(router.state.location.pathname).toBe("/uploads/u1/lots/10"))
  })

  it("shows a muted arrow at the ends of the list", async () => {
    await openLot(lotDetail({ lot: LOTS[0] }), { path: "/uploads/u1/lots/9" })
    const pager = await screen.findByRole("navigation", {
      name: en("header.neighbours", "lot"),
    })
    expect(within(pager).getAllByRole("link")).toHaveLength(1)
    expect(pager.querySelectorAll("[aria-hidden='true']").length).toBeGreaterThan(0)
  })
})

describe("on a narrow screen", () => {
  it("names the section to the screen reader after a choice", async () => {
    Object.assign(window, {
      matchMedia: vi.fn(() => ({
        matches: true,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
      })),
      scrollBy: vi.fn(),
    })
    const { user, router } = await openLot(undefined, {
      path: "/uploads/u1/lots/10?view=candidates",
    })
    expect(screen.getByRole("radio", { name: en("views.companies", "lot") })).toBeChecked()
    await user.click(screen.getByRole("button", { name: new RegExp(LONG_NAME) }))
    expect(router.state.location.search).toBe("?company=south")
    expect(screen.getByRole("heading", { level: 2, name: LONG_NAME })).toHaveFocus()
    Object.assign(window, { matchMedia: undefined })
  })
})
