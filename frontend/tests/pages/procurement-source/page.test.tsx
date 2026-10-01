import { screen } from "@testing-library/react"
import { renderPage, stubGateway } from "@tests/support/gateway"
import { afterEach, describe, expect, it, vi } from "vitest"
import { parsePurchaseSource } from "@/entities/recommendation/purchase-source"

const source = {
  provenance: "procurement_archive",
  title: "Office paper procurement",
  lot_id: "archive-1",
  supplier_inn: "1111111111",
  customer_inn: "2222222222",
  category: "17.12",
  source_system: "Archive",
  product_names: ["A4 paper"],
  is_winner: true,
  publish_date: "2024-11-06",
}
const path = "/uploads/u1/lots/paper/evidence/1111111111/archive-1"

afterEach(() => vi.unstubAllGlobals())

describe("procurement archive", () => {
  it("shows factual source data and links back to the recommendation", async () => {
    const fetcher = vi.fn(
      async (_input: RequestInfo | URL) => new Response(JSON.stringify(source)),
    )
    vi.stubGlobal("fetch", fetcher)
    renderPage(path, stubGateway())
    expect(
      await screen.findByRole("heading", { level: 1, name: source.title }),
    ).toBeInTheDocument()
    expect(screen.getByText("A4 paper")).toBeInTheDocument()
    expect(screen.getByText("Winner")).toBeInTheDocument()
    expect(screen.getByText("2222222222")).toBeInTheDocument()
    expect(screen.getByRole("link", { name: "Back to recommendation" })).toHaveAttribute(
      "href",
      "/uploads/u1/lots/paper",
    )
    expect(String(fetcher.mock.calls[0]?.[0])).toContain(
      "/api/uploads/u1/lots/paper/evidence/1111111111/archive-1",
    )
  })
  it("does not invent missing products, a customer or a winner", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(
        async () =>
          new Response(
            JSON.stringify({
              ...source,
              is_winner: false,
              product_names: [],
              customer_inn: "",
              source_system: "",
            }),
          ),
      ),
    )
    renderPage(path, stubGateway())
    expect(await screen.findByText("Participant")).toBeInTheDocument()
    expect(screen.getAllByText("Not given in archive")).toHaveLength(2)
    expect(screen.getByText("This record does not contain product names.")).toBeInTheDocument()
  })
  it("keeps the back link when the source is unavailable", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response("{}", { status: 404 })),
    )
    const { user } = renderPage(path, stubGateway())
    expect(
      await screen.findByRole("link", { name: "Back to recommendation" }),
    ).toBeInTheDocument()
    await user.click(screen.getByRole("button", { name: "Try again" }))
    expect(
      await screen.findByRole("link", { name: "Back to recommendation" }),
    ).toBeInTheDocument()
  })
  it("rejects an invalid outcome, date or provenance", () => {
    expect(() => parsePurchaseSource({ ...source, is_winner: "true" })).toThrow()
    expect(() => parsePurchaseSource({ ...source, publish_date: "invalid" })).toThrow()
    expect(() => parsePurchaseSource({ ...source, provenance: "unknown" })).toThrow()
  })
})
