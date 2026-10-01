import { contract } from "@tests/support/search"
import { describe, expect, it } from "vitest"
import { statusOf } from "@/entities/upload/model"
import {
  parseLotDetail,
  parseLotResults,
  parseUploadDetail,
  parseUploadList,
  parseUploadSummary,
} from "@/entities/upload/parse"

describe("the upload contract examples", () => {
  it.each([
    ["summary", (value: unknown) => parseUploadSummary(value)],
    ["list", parseUploadList],
    ["detail", parseUploadDetail],
    ["lot", parseLotDetail],
    ["results", parseLotResults],
  ] as const)("parse the %s example", (name, parse) => {
    expect(() => parse(contract(`upload/${name}.example.json`))).not.toThrow()
  })

  it("carry every status count, including failed lots", () => {
    const summary = parseUploadSummary(contract("upload/summary.example.json"))
    expect(summary.counts).toEqual({ ready: 0, needsCheck: 1, noCandidates: 1, failed: 0 })
    const detail = parseUploadDetail(contract("upload/detail.example.json"))
    expect(detail.lots.map((lot) => lot.status)).toEqual([
      "needsCheck",
      "noCandidates",
      "queued",
    ])
    expect(detail.lots[1]).not.toHaveProperty("subject")
  })

  it("describe a company with codes, not prose", () => {
    const { recommendation } = parseLotDetail(contract("upload/lot.example.json"))
    const [first, second] = recommendation?.companies ?? []
    expect(first?.checkReasons).toEqual(["rangeUnconfirmed"])
    expect(first?.highlights[0]).toEqual({
      code: "coversItems",
      params: { matched: 1, total: 2 },
    })
    expect(first?.purchases[0]).not.toHaveProperty("year")
    expect(first?.purchases[0]).not.toHaveProperty("source")
    expect(second?.contacts).toEqual({})
    expect(second?.matches[0]).not.toHaveProperty("source")
    const known = new Set(recommendation?.products.map((product) => product.id))
    const linked = recommendation?.companies.flatMap((company) =>
      company.matches.map((match) => match.productId),
    )
    expect(linked?.every((id) => known.has(id))).toBe(true)
  })

  it("carry search warnings of a lot", () => {
    const { recommendation } = parseLotDetail(contract("upload/lot.example.json"))
    expect(recommendation?.warnings).toEqual([{ code: "channelFailed", subject: "history" }])
    expect(recommendation && statusOf(recommendation)).toBe("needsCheck")
    const [, empty] = parseLotResults(contract("upload/results.example.json"))
    expect(empty?.recommendation?.warnings).toEqual([])
  })

  it("leave lots without candidates without companies", () => {
    const results = parseLotResults(contract("upload/results.example.json"))
    expect(results.map((result) => result.recommendation?.companies.length)).toEqual([2, 0])
  })

  it("send the requested lots as identifiers", () => {
    expect(contract("upload/results-request.example.json")).toEqual({
      lotIds: ["4257576", "4633163"],
    })
  })
})
