import { lotSummary } from "@tests/support/gateway"
import { describe, expect, it } from "vitest"
import {
  filterCounts,
  filtered,
  PAGE_SIZE,
  pageCount,
  pageForIndex,
  pageOf,
  readQuery,
  writeQuery,
} from "@/entities/upload/list-query"

describe("the list query", () => {
  it("round-trips through the address", () => {
    const query = readQuery(new URLSearchParams("q=milk&status=needsCheck&page=3"))
    expect(query).toEqual({ search: "milk", filter: "needsCheck", page: 3 })
    expect(writeQuery(query)).toBe("?q=milk&status=needsCheck&page=3")
    expect(readQuery(new URLSearchParams("status=odd&page=-2"))).toEqual({
      search: "",
      filter: "all",
      page: 1,
    })
    expect(writeQuery({ search: "", filter: "all", page: 1 })).toBe("")
  })

  it("searches the whole list and counts statuses", () => {
    const lots = [
      lotSummary("1", { title: "Milk", status: "ready" }),
      lotSummary("2", { title: "Bread", customerInn: "7811", status: "needsCheck" }),
      lotSummary("3", { title: "Paper", status: "queued" }),
      lotSummary("4", { title: "Ink", subject: "Printer milk", status: "noCandidates" }),
    ]
    expect(filtered(lots, { search: "MILK", filter: "all", page: 1 }).map((l) => l.id)).toEqual(
      ["1", "4"],
    )
    expect(filtered(lots, { search: "7811", filter: "needsCheck", page: 1 })).toHaveLength(1)
    expect(filtered(lots, { search: " ", filter: "ready", page: 1 })).toHaveLength(1)
    expect(filterCounts(lots)).toEqual({ all: 4, ready: 1, needsCheck: 1, noCandidates: 1 })
  })

  it("pages through results", () => {
    const items = Array.from({ length: PAGE_SIZE * 2 + 1 }, (_, index) => index)
    expect(pageCount(items.length)).toBe(3)
    expect(pageCount(0)).toBe(1)
    expect(pageOf(items, 3)).toEqual([PAGE_SIZE * 2])
    expect(pageOf(items, 9)).toEqual([PAGE_SIZE * 2])
    expect(pageForIndex(PAGE_SIZE)).toBe(2)
    expect(pageForIndex(-1)).toBe(1)
  })
})
