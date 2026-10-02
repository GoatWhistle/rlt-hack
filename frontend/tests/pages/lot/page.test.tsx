import { screen, waitFor, within } from "@testing-library/react"
import { en } from "@tests/support/dictionaries"
import { lotSummary, renderPage, stubGateway, uploadDetail } from "@tests/support/gateway"
import { contractResult } from "@tests/support/search"
import { describe, expect, it, vi } from "vitest"
import { ApiError } from "@/shared/api/api-error"
import { LOTS, lotDetail, openLot } from "./open-lot"

describe("the purchase header", () => {
  it("names the purchase once with its lot, customer, price and date", async () => {
    await openLot()
    expect(screen.getByRole("heading", { level: 1, name: "Food supply" })).toBeInTheDocument()
    expect(screen.getByText("Lot 10")).toBeInTheDocument()
    expect(screen.getByText("Customer INN 7800000001")).toBeInTheDocument()
    expect(screen.getByText(/Start price/)).toBeInTheDocument()
    expect(screen.getByText("Published Feb 3, 2025")).toBeInTheDocument()
  })

  it("returns to the same list page and walks to neighbouring purchases", async () => {
    await openLot(undefined, { path: "/uploads/u1/lots/10?status=ready" })
    expect(
      await screen.findByRole("navigation", { name: en("header.neighbours", "lot") }),
    ).toHaveTextContent("2 of 3")
    expect(screen.getByRole("link", { name: /Purchases · notices\.csv/ })).toHaveAttribute(
      "href",
      "/uploads/u1?status=ready",
    )
    expect(screen.getByRole("link", { name: en("header.prev", "lot") })).toHaveAttribute(
      "href",
      "/uploads/u1/lots/9?status=ready",
    )
    expect(screen.getByRole("link", { name: en("header.next", "lot") })).toHaveAttribute(
      "href",
      "/uploads/u1/lots/11?status=ready",
    )
  })

  it("explains a missing purchase and links back", async () => {
    const gateway = stubGateway({
      get: vi.fn(async () => uploadDetail(LOTS)),
      lot: vi.fn(async () => Promise.reject(new ApiError({ status: 404, code: "notFound" }))),
    })
    renderPage("/uploads/u1/lots/404", gateway)
    expect(
      await screen.findByRole("heading", { name: en("missing.title", "lot") }),
    ).toBeInTheDocument()
    expect(
      await screen.findByRole("link", { name: en("missing.toFile", "lot") }),
    ).toHaveAttribute("href", "/uploads/u1")
    expect(screen.getByRole("link", { name: en("missing.toUploads", "lot") })).toHaveAttribute(
      "href",
      "/uploads",
    )
  })

  it("offers a retry when the purchase cannot load", async () => {
    const gateway = stubGateway({
      lot: vi.fn(async () => Promise.reject(new ApiError({ status: 500, code: "server" }))),
    })
    renderPage("/uploads/u1/lots/10", gateway)
    await waitFor(
      () =>
        expect(screen.getByRole("button", { name: en("action.retry") })).toBeInTheDocument(),
      { timeout: 6000 },
    )
  })

  it.each([
    ["queued", "queued.title"],
    ["failed", "failed.title"],
    ["noCandidates", "notUnderstood.title"],
    ["ready", "unavailable.title"],
  ] as const)("explains a %s purchase without a saved search", async (status, title) => {
    const lot = lotSummary("10", { title: "Food supply", status })
    await openLot(lotDetail({ lot, search: undefined }))
    expect(screen.getByRole("heading", { name: en(title, "lot") })).toBeInTheDocument()
  })

  it("downloads this purchase from the header", async () => {
    const { user } = await openLot()
    await user.click(screen.getByRole("button", { name: en("header.export", "lot") }))
    const dialog = await screen.findByRole("dialog", { name: en("title", "export") })
    expect(within(dialog).getByRole("radio", { name: en("lots.lot", "export") })).toBeChecked()
  })
})

describe("the shared result workspace", () => {
  it("shows the same candidates and evidence as a manual search", async () => {
    await openLot()
    const result = contractResult()
    const first = result.candidates[0]
    if (!first) throw new Error("the contract has candidates")
    expect(screen.getAllByText(first.name).length).toBeGreaterThan(0)
    for (const item of result.items) {
      expect(screen.getAllByText(item.name).length).toBeGreaterThan(0)
    }
  })

  it("keeps the search warnings visible", async () => {
    const search = contractResult((payload) => ({
      ...payload,
      warnings: [{ code: "channelFailed", subject: "semantic" }],
    }))
    await openLot(lotDetail({ search }))
    expect(screen.getByRole("note")).toBeInTheDocument()
  })
})
