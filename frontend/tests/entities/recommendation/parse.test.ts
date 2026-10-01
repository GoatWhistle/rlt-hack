import { describe, expect, it } from "vitest"
import { PayloadFormatError, parseRecommendation } from "@/entities/recommendation/parse"
import { recommendationFixture } from "./fixture"

type Node = Record<string | number, unknown>

function changed(path: readonly (string | number)[], value: unknown): unknown {
  const copy = structuredClone(recommendationFixture) as unknown as Node
  const parent = path.slice(0, -1).reduce<Node>((node, key) => node[key] as Node, copy)
  const last = path[path.length - 1] ?? ""
  if (value === undefined) delete parent[last]
  else parent[last] = value
  return copy
}

describe("parseRecommendation", () => {
  it("accepts a well-formed payload", () => {
    expect(parseRecommendation(structuredClone(recommendationFixture))).toEqual(
      recommendationFixture,
    )
  })

  it("treats null optional fields as absent", () => {
    const payload = changed(["companies", 0, "purchases", 0, "year"], null) as Node
    const north = (payload.companies as Node[])[0] as Node
    ;(north.purchases as Node[])[0] = {
      title: "Lot 41",
      year: null,
      outcome: "winner",
      source: null,
    }
    ;(north.matches as Node[])[0] = { productId: "sugar", basis: "inferred", source: null }
    north.contacts = { site: "", email: "", phone: "" }
    const parsed = parseRecommendation(payload)
    expect(parsed.companies[0]?.purchases[0]).toEqual({ title: "Lot 41", outcome: "winner" })
    expect(parsed.companies[0]?.matches[0]).not.toHaveProperty("source")
    expect(parsed.companies[0]?.contacts).toEqual({})
  })

  it("keeps check reasons and highlights as codes", () => {
    const [north, south] = parseRecommendation(structuredClone(recommendationFixture)).companies
    expect(north?.checkReasons).toEqual([])
    expect(north?.highlights[0]).toEqual({
      code: "coversItems",
      params: { matched: 5, total: 5 },
    })
    expect(south?.checkReasons).toEqual(["rangeUnconfirmed"])
  })

  it("skips codes added by a newer backend", () => {
    const payload = changed(
      ["companies", 1, "checkReasons"],
      ["rangeUnconfirmed", "taxDebt"],
    ) as Node
    const north = (payload.companies as Node[])[0] as Node
    north.highlights = [{ code: "cheap", params: {} }, ...(north.highlights as Node[])]
    payload.warnings = [{ code: "solarFlare" }, { code: "channelFailed", subject: "history" }]
    const parsed = parseRecommendation(payload)
    expect(parsed.companies[1]?.checkReasons).toEqual(["rangeUnconfirmed"])
    expect(parsed.companies[0]?.highlights[0]?.code).toBe("coversItems")
    expect(parsed.warnings).toEqual([{ code: "channelFailed", subject: "history" }])
  })

  it("treats absent warnings as an older backend", () => {
    expect(parseRecommendation(structuredClone(recommendationFixture))).not.toHaveProperty(
      "warnings",
    )
    expect(parseRecommendation(changed(["warnings"], null))).not.toHaveProperty("warnings")
  })

  it.each([
    ["a non-object payload", null, "$"],
    ["an array payload", [], "$"],
    ["a missing title", changed(["requestTitle"], undefined), "$.requestTitle"],
    ["products that are not a list", changed(["products"], {}), "$.products"],
    [
      "an unknown product origin",
      changed(["products", 0, "origin"], "guess"),
      "$.products[0].origin",
    ],
    [
      "a note that is not an object",
      changed(["products", 1, "originNote"], 3),
      "$.products[1].originNote",
    ],
    [
      "an unknown note code",
      changed(["products", 1, "originNote", "code"], "hunch"),
      "$.products[1].originNote.code",
    ],
    [
      "a similar-purchases note without counts",
      changed(["products", 1, "originNote", "hits"], undefined),
      "$.products[1].originNote.hits",
    ],
    [
      "an unknown company role",
      changed(["companies", 0, "role"], "Supplier"),
      "$.companies[0].role",
    ],
    [
      "a check reason that is not text",
      changed(["companies", 1, "checkReasons"], [7]),
      "$.companies[1].checkReasons[0]",
    ],
    [
      "check reasons that are not a list",
      changed(["companies", 1, "checkReasons"], "rangeUnconfirmed"),
      "$.companies[1].checkReasons",
    ],
    [
      "a missing highlight list",
      changed(["companies", 0, "highlights"], undefined),
      "$.companies[0].highlights",
    ],
    [
      "a highlight code that is not text",
      changed(["companies", 0, "highlights", 0, "code"], 3),
      "$.companies[0].highlights[0].code",
    ],
    ["warnings that are not a list", changed(["warnings"], "channelFailed"), "$.warnings"],
    [
      "a highlight parameter that is not a count",
      changed(["companies", 0, "highlights", 0, "params", "matched"], "five"),
      "$.companies[0].highlights[0].params.matched",
    ],
    [
      "a purchase year that is not a count",
      changed(["companies", 0, "purchases", 0, "year"], "2024"),
      "$.companies[0].purchases[0].year",
    ],
    [
      "a purchase lot that is not text",
      changed(["companies", 0, "purchases", 0, "lotId"], 42),
      "$.companies[0].purchases[0].lotId",
    ],
    [
      "an unknown company status",
      changed(["companies", 1, "status"], "maybe"),
      "$.companies[1].status",
    ],
    [
      "a negative purchase count",
      changed(["companies", 0, "similarPurchases"], -1),
      "$.companies[0].similarPurchases",
    ],
    ["a fractional win count", changed(["companies", 0, "wins"], 1.5), "$.companies[0].wins"],
    [
      "an unknown match basis",
      changed(["companies", 0, "matches", 0, "basis"], "rumour"),
      "$.companies[0].matches[0].basis",
    ],
    [
      "an unknown source kind",
      changed(["companies", 0, "matches", 1, "source", "kind"], "blog"),
      "$.companies[0].matches[1].source.kind",
    ],
    [
      "a source that is not an object",
      changed(["companies", 0, "purchases", 0, "source"], "link"),
      "$.companies[0].purchases[0].source",
    ],
    [
      "an unknown purchase outcome",
      changed(["companies", 0, "purchases", 0, "outcome"], "lost"),
      "$.companies[0].purchases[0].outcome",
    ],
  ])("rejects %s", (_, payload, path) => {
    expect(() => parseRecommendation(payload)).toThrow(new PayloadFormatError(path).message)
  })
})
