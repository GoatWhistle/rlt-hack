import { describe, expect, it } from "vitest"
import { knownList, knownOf, PayloadFormatError } from "@/shared/api/payload"

const COLORS = ["red", "green"] as const

describe("tolerant code lists", () => {
  it("keeps known codes and drops new ones", () => {
    const fields = { colors: ["red", "violet", "green"] }
    expect(knownList(fields, "colors", "$", (entry, at) => knownOf(COLORS, entry, at))).toEqual(
      ["red", "green"],
    )
  })

  it("still rejects values that are not codes", () => {
    expect(() => knownOf(COLORS, 3, "$.color")).toThrow(PayloadFormatError)
    expect(() => knownList({ colors: "red" }, "colors", "$", () => undefined)).toThrow(
      PayloadFormatError,
    )
  })
})
