import { describe, expect, it } from "vitest"
import { parseRecommendation, RecommendationFormatError } from "@/entities/recommendation/parse"
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
      "an unknown company status",
      changed(["companies", 1, "status"], "maybe"),
      "$.companies[1].status",
    ],
    [
      "a purchase count that is not a number",
      changed(["companies", 0, "similarPurchases"], "1"),
      "$.companies[0].similarPurchases",
    ],
    [
      "a reason that is not text",
      changed(["companies", 0, "why"], [1]),
      "$.companies[0].why[0]",
    ],
  ])("rejects %s", (_, payload, path) => {
    expect(() => parseRecommendation(payload)).toThrow(
      new RecommendationFormatError(path).message,
    )
  })
})
