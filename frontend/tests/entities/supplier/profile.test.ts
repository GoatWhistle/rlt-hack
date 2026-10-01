import { contract } from "@tests/support/search"
import { describe, expect, it, vi } from "vitest"
import { createHttpSupplierGateway, SUPPLIERS_PATH } from "@/entities/supplier/gateway"
import { parseSupplierProfile } from "@/entities/supplier/parse"
import { createHttpClient } from "@/shared/api/http-client"
import { PayloadFormatError } from "@/shared/api/payload"

type Node = Record<string, unknown>

function profile(): Node {
  return contract("supplier/profile.example.json") as Node
}

describe("the supplier profile contract", () => {
  it("reads the profile example", () => {
    const parsed = parseSupplierProfile(profile())
    expect(parsed).toMatchObject({
      inn: "7801234567",
      kpps: ["780101001"],
      identity: "verified",
      role: "supplierDistributor",
    })
    expect(parsed.offers[0]).toMatchObject({
      price: 84.5,
      currency: "RUB",
      availability: "available",
      source: { kind: "price" },
    })
  })

  it("accepts an offer without a price and rejects broken ones", () => {
    const payload = profile()
    const offer = (payload.offers as Node[])[0] as Node
    offer.price = null
    expect(parseSupplierProfile(payload).offers[0]?.price).toBeUndefined()
    offer.price = "cheap"
    expect(() => parseSupplierProfile(payload)).toThrow(PayloadFormatError)
    offer.price = "1.00"
    offer.availability = "tomorrow"
    expect(() => parseSupplierProfile(payload)).toThrow(PayloadFormatError)
    expect(() => parseSupplierProfile({ ...profile(), identity: "maybe" })).toThrow(
      PayloadFormatError,
    )
  })

  it("is fetched by id over http", async () => {
    const fetcher = vi.fn(
      async (_url: RequestInfo | URL, _init?: RequestInit) =>
        new Response(JSON.stringify(profile())),
    )
    const gateway = createHttpSupplierGateway(createHttpClient({ baseUrl: "/api", fetcher }))
    expect((await gateway.profile("6c1e")).name).toBe("ООО «Северный Провиант»")
    expect(fetcher.mock.calls[0]?.[0]).toBe(`/api${SUPPLIERS_PATH}/6c1e`)
  })
})
