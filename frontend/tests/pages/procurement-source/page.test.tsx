import { screen } from "@testing-library/react"
import { renderPage, stubGateway } from "@tests/support/gateway"
import { contract } from "@tests/support/search"
import { afterEach, describe, expect, it, vi } from "vitest"
import { parsePurchaseSource } from "@/entities/supplier/purchase-source"

const source = contract("supplier/purchase.example.json") as Record<string, unknown>
const back = "/search/s1?candidate=c1"
const path = `/suppliers/c1/purchases/4012345?back=${encodeURIComponent(back)}`

afterEach(() => vi.unstubAllGlobals())

describe("procurement archive", () => {
  it("shows factual source data and links back to where it was opened", async () => {
    const fetcher = vi.fn(
      async (_input: RequestInfo | URL) => new Response(JSON.stringify(source)),
    )
    vi.stubGlobal("fetch", fetcher)
    renderPage(path, stubGateway())
    expect(
      await screen.findByRole("heading", { level: 1, name: String(source.title) }),
    ).toBeInTheDocument()
    expect(screen.getByText("Рис шлифованный")).toBeInTheDocument()
    expect(screen.getByText("Winner")).toBeInTheDocument()
    expect(screen.getByText("7807022750")).toBeInTheDocument()
    expect(screen.getByRole("link", { name: "Back to recommendation" })).toHaveAttribute(
      "href",
      back,
    )
    expect(String(fetcher.mock.calls[0]?.[0])).toContain("/api/suppliers/c1/purchases/4012345")
  })

  it("does not invent missing products, a customer or a winner", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(
        async () =>
          new Response(
            JSON.stringify({
              ...source,
              outcome: "participant",
              products: [],
              customerInn: null,
              sourceSystem: "",
            }),
          ),
      ),
    )
    renderPage(path, stubGateway())
    expect(await screen.findByText("Participant")).toBeInTheDocument()
    expect(screen.getAllByText("Not given in archive")).toHaveLength(2)
    expect(screen.getByText("This record does not contain product names.")).toBeInTheDocument()
  })

  it("keeps a safe back link when the source is unavailable", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response("{}", { status: 404 })),
    )
    const { user } = renderPage(
      "/suppliers/c1/purchases/1?back=https://evil.example",
      stubGateway(),
    )
    const link = await screen.findByRole("link", { name: "Back to recommendation" })
    expect(link).toHaveAttribute("href", "/search")
    await user.click(screen.getByRole("button", { name: "Try again" }))
    expect(
      await screen.findByRole("link", { name: "Back to recommendation" }),
    ).toBeInTheDocument()
  })

  it("rejects an invalid outcome, date or provenance", () => {
    expect(() => parsePurchaseSource({ ...source, outcome: "lost" })).toThrow()
    expect(() => parsePurchaseSource({ ...source, publishedAt: "invalid" })).toThrow()
    expect(() => parsePurchaseSource({ ...source, provenance: "unknown" })).toThrow()
  })
})
