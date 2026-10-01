import { contract } from "@tests/support/search"
import { describe, expect, it } from "vitest"
import { parseRecentSearches, parseSearchResult } from "@/entities/search/parse"
import { PayloadFormatError } from "@/shared/api/payload"

type Node = Record<string | number, unknown>

function response(): Node {
  return contract("search/response.example.json") as Node
}

function changed(path: readonly (string | number)[], value: unknown): Node {
  const copy = response()
  const parent = path.slice(0, -1).reduce<Node>((node, key) => node[key] as Node, copy)
  const last = path[path.length - 1] ?? ""
  if (value === undefined) delete parent[last]
  else parent[last] = value
  return copy
}

describe("the search contract", () => {
  it("reads the response example", () => {
    const result = parseSearchResult(response())
    expect(result.searchId).toBe("1f0c3b5e-6a1d-4c2e-9f7a-2b8d4e6f1a90")
    expect(result.query).toMatchObject({ locale: "ru", limit: 20 })
    expect(result.query.filters).toEqual({ regions: ["78"], itemType: "goods" })
    expect(result.items[0]?.quantity).toEqual({ value: "500", unit: "кг" })
    const [first, second] = result.candidates
    expect(first?.matches[0]?.source?.kind).toBe("price")
    expect(first?.highlights[0]).toEqual({
      code: "coversItems",
      params: { matched: 2, total: 2 },
    })
    expect(first?.score.channels).toEqual([{ channel: "lexical", rank: 1 }])
    expect(second?.roleSource).toBeUndefined()
    expect(second?.matches[0]).toEqual({ itemId: "i1", basis: "inferred" })
    expect(second?.contacts).toEqual({})
    expect(second?.checkReasons).toEqual([
      "innMissing",
      "roleUnconfirmed",
      "noCurrentOffer",
      "rangeUnconfirmed",
    ])
  })

  it("reads the recent searches example", () => {
    expect(parseRecentSearches(contract("search/recent.example.json"))).toEqual([
      {
        searchId: "1f0c3b5e-6a1d-4c2e-9f7a-2b8d4e6f1a90",
        text: "Крупа гречневая ядрица 500 кг; рис шлифованный 200 кг",
        locale: "ru",
        items: 2,
        candidates: 2,
        recommended: 1,
        createdAt: "2026-10-01T12:00:00Z",
      },
    ])
  })

  it("accepts absent filters, quantity and warning subject", () => {
    const payload = changed(["query", "filters"], null)
    ;(payload.items as Node[])[0] = { ...((payload.items as Node[])[0] ?? {}), quantity: null }
    payload.warnings = [{ code: "channelFailed" }]
    const result = parseSearchResult(payload)
    expect(result.query.filters).toEqual({})
    expect(result.items[0]?.quantity).toBeUndefined()
    expect(result.warnings).toEqual([{ code: "channelFailed", subject: "" }])
  })

  it.each([
    ["a check reason that is not text", ["candidates", 1, "checkReasons", 0], 5],
    ["a highlight code that is not text", ["candidates", 0, "highlights", 0, "code"], 5],
    ["an unknown role", ["candidates", 0, "role"], "broker"],
    ["an unknown basis", ["candidates", 0, "matches", 0, "basis"], "rumour"],
    ["an unknown source kind", ["candidates", 0, "roleSource", "kind"], "blog"],
    ["an unknown status", ["candidates", 0, "status"], "great"],
    ["an unknown item origin", ["items", 0, "origin"], "dream"],
    ["an unknown locale", ["query", "locale"], "de"],
    ["a score above one", ["candidates", 0, "score", "total"], 1.5],
    ["a score that is not a number", ["candidates", 0, "score", "fusion"], "high"],
    ["a fractional count", ["candidates", 0, "history", "wins"], 1.5],
    [
      "a highlight parameter that is not a count",
      ["candidates", 0, "highlights", 0, "params", "matched"],
      "two",
    ],
    ["a missing history", ["candidates", 0, "history"], undefined],
    ["candidates that are not a list", ["candidates"], {}],
    ["a match to an unknown item", ["candidates", 0, "matches", 0, "itemId"], "i9"],
    ["a quantity without a unit", ["items", 0, "quantity", "unit"], undefined],
  ])("rejects %s", (_name, path, value) => {
    expect(() => parseSearchResult(changed(path, value))).toThrow(PayloadFormatError)
  })

  it("skips codes added by a newer backend", () => {
    const payload = changed(["candidates", 1, "checkReasons", 0], "taxDebt")
    payload.warnings = [{ code: "solarFlare" }, { code: "archiveFailed" }]
    const result = parseSearchResult(payload)
    expect(result.warnings).toEqual([{ code: "archiveFailed", subject: "" }])
    expect(result.candidates[1]?.checkReasons).not.toContain("taxDebt")
  })

  it("rejects a broken warning and a broken recent list", () => {
    const payload = response()
    payload.warnings = [{ code: 5 }]
    expect(() => parseSearchResult(payload)).toThrow(PayloadFormatError)
    expect(() => parseRecentSearches({ searches: [{ searchId: 1 }] })).toThrow(
      PayloadFormatError,
    )
    expect(() => parseRecentSearches([])).toThrow(PayloadFormatError)
  })
})
