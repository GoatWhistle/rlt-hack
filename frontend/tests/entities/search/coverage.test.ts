import { contract, contractResult } from "@tests/support/search"
import { describe, expect, it } from "vitest"
import { cellState, coverageOf } from "@/entities/search/coverage"
import { parseSearchResult } from "@/entities/search/parse"

const requirements = parseSearchResult(contract("search/cases/requirements.example.json"))

describe("coverage of the items", () => {
  it("tells an offer, an assumption, a contradiction and missing data apart", () => {
    const [matching, incomplete, conflicting] = requirements.candidates
    if (!matching || !incomplete || !conflicting) throw new Error("case has four candidates")
    expect(cellState(matching, "i1")).toBe("offer")
    expect(cellState(incomplete, "i1")).toBe("assumed")
    expect(cellState(conflicting, "i1")).toBe("conflict")
    expect(cellState(matching, "ghost")).toBe("insufficient")
  })

  it("never adds assumptions to the confirmed count", () => {
    const [matching, incomplete, conflicting] = requirements.candidates
    if (!matching || !incomplete || !conflicting) throw new Error("case has four candidates")
    expect(coverageOf(matching, requirements.items)).toEqual({
      confirmed: 1,
      toClarify: 0,
      missing: 0,
      total: 1,
    })
    expect(coverageOf(incomplete, requirements.items).toClarify).toBe(1)
    expect(coverageOf(conflicting, requirements.items).missing).toBe(1)
  })

  it("separates registry records and past experience", () => {
    const base = contractResult()
    const [lead, other] = base.candidates
    if (!lead || !other) throw new Error("contract has two candidates")
    const registered = {
      ...lead,
      matches: lead.matches.map((match) =>
        match.offer
          ? { ...match, offer: { ...match.offer, sourceType: "registry" as const } }
          : match,
      ),
    }
    expect(cellState(registered, "i1")).toBe("registered")
    const experienced = {
      ...other,
      matches: [],
      history: {
        ...other.history,
        records: [{ lotId: "L1", title: "t", outcome: "winner" as const, itemIds: ["i2"] }],
      },
    }
    expect(cellState(experienced, "i2")).toBe("history")
  })
})
