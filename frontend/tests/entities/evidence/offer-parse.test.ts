import { contract } from "@tests/support/search"
import { describe, expect, it } from "vitest"
import { isStale, STALE_AFTER_DAYS } from "@/entities/evidence/model"
import { parseOffer, parseOfferMap } from "@/entities/evidence/offer-parse"
import { parseSearchResult } from "@/entities/search/parse"
import { candidateView } from "@/entities/search/view"
import { parseSupplierProfile } from "@/entities/supplier/parse"
import { PayloadFormatError } from "@/shared/api/payload"

type Node = Record<string, unknown>

const OFFER_ID = "9a8b7c6d-5e4f-4a3b-9c2d-1e0f9a8b7c6d"

function response(): Node {
  return contract("search/response.example.json") as Node
}

function offer(extra: Node = {}): Node {
  return { id: "o1", name: "Offer", availability: "available", ...extra }
}

describe("offers in the search contract", () => {
  it("reads the offer dictionary and links it to the matches", () => {
    const result = parseSearchResult(response())
    expect(Object.keys(result.offers)).toHaveLength(2)
    expect(result.offers[OFFER_ID]).toEqual({
      id: OFFER_ID,
      name: "Крупа гречневая ядрица 1 сорт, мешок 50 кг",
      price: 84.5,
      currency: "RUB",
      unit: "кг",
      availability: "available",
      brand: "Увелка",
      article: "4607012",
      okpd2: "10.61.32.110",
      attributes: [
        { name: "Фасовка", value: "50 кг" },
        { name: "Сорт", value: "первый" },
      ],
      seller: "verified",
      source: {
        kind: "price",
        title: "Прайс-лист компании",
        url: "https://severny-proviant.example.org/price/grechka",
        checkedAt: "2026-09-29T08:00:00Z",
      },
    })
    const [first, second] = result.candidates
    const view = first && candidateView(first, result.offers)
    expect(view?.matches[0]?.offer?.id).toBe(OFFER_ID)
    expect(second && candidateView(second, result.offers).matches[0]?.offer).toBeUndefined()
  })

  it("accepts a result archived before offers existed", () => {
    const payload = response()
    delete payload.offers
    const result = parseSearchResult(payload)
    expect(result.offers).toEqual({})
    const first = result.candidates[0]
    expect(first && candidateView(first).matches[0]?.offer).toBeUndefined()
    expect(parseOfferMap(null, "$.offers")).toEqual({})
  })

  it("rejects an offer filed under another id", () => {
    const payload = response()
    const offers = payload.offers as Node
    offers.other = offers[OFFER_ID]
    expect(() => parseSearchResult(payload)).toThrow(PayloadFormatError)
  })

  it("reads the same offer fields in the company profile", () => {
    const profile = parseSupplierProfile(contract("supplier/profile.example.json"))
    expect(profile.offers[0]).toMatchObject({
      brand: "Увелка",
      okpd2: "10.61.32.110",
      seller: "verified",
      attributes: [{ name: "Фасовка", value: "50 кг" }, expect.anything()],
    })
    expect(profile.offers[0]?.imageUrl).toBeUndefined()
  })
})

describe("a single offer", () => {
  it("drops empty fields instead of inventing them", () => {
    expect(
      parseOffer(
        offer({
          price: null,
          currency: "",
          unit: " ",
          brand: "",
          article: "",
          okpd2: "",
          attributes: [{ name: "", value: "x" }],
          imageUrl: null,
          source: null,
        }),
        "$",
      ),
    ).toEqual({ id: "o1", name: "Offer", availability: "available" })
  })

  it("keeps only web images", () => {
    expect(
      parseOffer(offer({ imageUrl: "https://img.example.org/a.webp" }), "$").imageUrl,
    ).toBe("https://img.example.org/a.webp")
    expect(parseOffer(offer({ imageUrl: "javascript:alert(1)" }), "$").imageUrl).toBeUndefined()
  })

  it("rejects broken offers", () => {
    expect(() => parseOffer(offer({ price: "cheap" }), "$")).toThrow(PayloadFormatError)
    expect(() => parseOffer(offer({ availability: "soon" }), "$")).toThrow(PayloadFormatError)
    expect(() => parseOffer(offer({ seller: "maybe" }), "$")).toThrow(PayloadFormatError)
    expect(() => parseOffer(offer({ attributes: [{ name: "a" }] }), "$")).toThrow(
      PayloadFormatError,
    )
  })
})

describe("stale sources", () => {
  const now = Date.parse("2026-10-02T00:00:00Z")

  it("are older than the threshold", () => {
    expect(STALE_AFTER_DAYS).toBe(30)
    expect(isStale("2026-08-01T00:00:00Z", now)).toBe(true)
    expect(isStale("2026-09-29T08:00:00Z", now)).toBe(false)
    expect(isStale(undefined, now)).toBe(false)
    expect(isStale("someday", now)).toBe(false)
  })
})
