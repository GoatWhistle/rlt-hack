import { screen, waitFor, within } from "@testing-library/react"
import { en, text } from "@tests/support/dictionaries"
import { renderPage, stubGateway, uploadDetail } from "@tests/support/gateway"
import { describe, expect, it, vi } from "vitest"
import { ApiError } from "@/shared/api/api-error"
import { LONG_NAME, recommendationFixture } from "../../entities/recommendation/fixture"
import { LOTS, lotDetail, openLot } from "./open-lot"

describe("the purchase header", () => {
  it("names the purchase once with its lot, customer, price and date", async () => {
    await openLot()
    expect(screen.getByRole("heading", { level: 1, name: "Food supply" })).toBeInTheDocument()
    expect(screen.getByText("Lot 10")).toBeInTheDocument()
    expect(screen.getByText("Customer INN 7800000001")).toBeInTheDocument()
    expect(screen.getByText(/Start price/)).toBeInTheDocument()
    expect(screen.getByText("Published Feb 3, 2025")).toBeInTheDocument()
    expect(screen.queryByRole("list", { name: en("chain.label", "lot") })).toBeNull()
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

  it("waits for a queued purchase and explains an empty result", async () => {
    const queued = lotDetail({ recommendation: undefined })
    await openLot(queued)
    expect(screen.getByRole("heading", { name: en("queued.title", "lot") })).toBeInTheDocument()
  })

  it("keeps the products when no candidate was found", async () => {
    await openLot(lotDetail({ recommendation: { ...recommendationFixture, companies: [] } }))
    expect(
      screen.getByRole("heading", { name: en("noCandidates.title", "lot") }),
    ).toBeInTheDocument()
    expect(
      screen.getByRole("region", { name: en("products.title", "lot") }),
    ).toBeInTheDocument()
  })

  it("downloads this purchase from the header", async () => {
    const { user } = await openLot()
    await user.click(screen.getByRole("button", { name: en("header.export", "lot") }))
    const dialog = await screen.findByRole("dialog", { name: en("title", "export") })
    expect(within(dialog).getByRole("radio", { name: en("lots.lot", "export") })).toBeChecked()
  })
})

describe("the products column", () => {
  it("labels the origin briefly and explains it on demand", async () => {
    const { user } = await openLot()
    const products = screen.getByRole("region", { name: en("products.title", "lot") })
    expect(within(products).getAllByText(en("products.origin.notice", "lot"))).toHaveLength(3)
    expect(
      within(products).getByText(en("products.origin.inferred", "lot")),
    ).toBeInTheDocument()
    const sugar = within(products).getByText("Sugar").closest("details")
    await user.click(within(products).getByText("Sugar"))
    expect(sugar).toHaveAttribute("open")
    expect(within(products).getByText("Seen in 8 of 10 similar purchases.")).toBeVisible()
    expect(within(products).getByText("OKPD2 10.81.12")).toBeVisible()
  })

  it("filters candidates by a product and shows how to reset", async () => {
    const { user } = await openLot()
    const filter = screen.getByRole("button", { name: "Show candidates with “Tea”" })
    await user.click(filter)
    expect(filter).toHaveAttribute("aria-pressed", "true")
    const companies = screen.getByRole("region", { name: en("companies.title", "lot") })
    expect(within(companies).getByText("Candidates with “Tea”")).toBeInTheDocument()
    expect(within(companies).getAllByRole("button", { pressed: false })).toHaveLength(1)
    await user.click(screen.getByRole("button", { name: "Show candidates with “Salt”" }))
    expect(within(companies).queryByRole("button", { name: new RegExp(LONG_NAME) })).toBeNull()
    await user.click(
      within(companies).getByRole("button", { name: en("companies.resetFilter", "lot") }),
    )
    expect(within(companies).getByRole("button", { name: /West Trade/ })).toBeInTheDocument()
  })

  it("says so when no candidate has the product", async () => {
    const recommendation = {
      ...recommendationFixture,
      products: [
        ...recommendationFixture.products,
        { id: "ghost", name: "Ghost", okpd2: "0", origin: "notice" as const },
      ],
    }
    const { user } = await openLot(lotDetail({ recommendation }))
    await user.click(screen.getByRole("button", { name: "Show candidates with “Ghost”" }))
    expect(screen.getByText(en("companies.noMatch", "lot"))).toBeInTheDocument()
    expect(screen.getByRole("article", { name: "North Foods" })).toBeInTheDocument()
  })
})

describe("in russian", () => {
  it("uses the right plural forms", async () => {
    await openLot(undefined, { locale: "ru" })
    expect(screen.getByText("5 позиций")).toBeInTheDocument()
    expect(screen.getByText("5 из 5 · 11 закупок")).toBeInTheDocument()
    expect(screen.getByText(text("ru", "lot", "evidence.summaryTitle"))).toBeInTheDocument()
  })
})
