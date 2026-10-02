import { describe, expect, it } from "vitest"
import {
  hasFilters,
  readFilters,
  readOffset,
  readProblem,
  recordsHref,
  writeFilters,
} from "@/entities/analytics/scope"

describe("analytics filters in the address", () => {
  it("reads only known values", () => {
    const params = new URLSearchParams("source=s1&type=registry&region= 78 ")
    expect(readFilters(params)).toEqual({
      sourceId: "s1",
      sourceType: "registry",
      region: "78",
    })
    expect(readFilters(new URLSearchParams("type=bogus"))).toEqual({})
  })

  it("writes them back and keeps unrelated parameters", () => {
    const extra = new URLSearchParams("page=2&source=old")
    expect(writeFilters({ sourceType: "feed", region: "78" }, extra)).toBe(
      "?page=2&type=feed&region=78",
    )
    expect(writeFilters({})).toBe("")
  })

  it("tells whether anything is applied", () => {
    expect(hasFilters({})).toBe(false)
    expect(hasFilters({ region: "78" })).toBe(true)
  })

  it("builds the link to the records behind a number", () => {
    expect(recordsHref({ sourceId: "s1" }, { problem: "stale", category: "01.11" })).toBe(
      "/analytics/records?problem=stale&category=01.11&source=s1",
    )
    expect(recordsHref({})).toBe("/analytics/records")
  })

  it("reads the problem and the page offset", () => {
    expect(readProblem(new URLSearchParams("problem=no_price"))).toBe("no_price")
    expect(readProblem(new URLSearchParams("problem=x"))).toBeUndefined()
    expect(readOffset(new URLSearchParams("page=3"))).toBe(50)
    expect(readOffset(new URLSearchParams("page=0"))).toBe(0)
  })
})
