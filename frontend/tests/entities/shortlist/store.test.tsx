import { act, renderHook } from "@testing-library/react"
import { afterEach, describe, expect, it } from "vitest"
import {
  resetShortlists,
  SHORTLIST_KEY,
  shortlistsOf,
  toggleShortlisted,
  useShortlist,
} from "@/entities/shortlist/store"
import { readLastUpload, rememberUpload } from "@/entities/upload/last-upload"

afterEach(() => resetShortlists())

describe("the shortlist", () => {
  it("toggles chosen companies per lot and keeps them in the browser", () => {
    const { result } = renderHook(() => useShortlist("u1", "lot"))
    expect(result.current.ids).toEqual([])
    act(() => result.current.toggle("a"))
    act(() => result.current.toggle("b"))
    expect(result.current.ids).toEqual(["a", "b"])
    act(() => result.current.toggle("a"))
    expect(result.current.ids).toEqual(["b"])
    expect(JSON.parse(localStorage.getItem(SHORTLIST_KEY) ?? "{}")).toEqual({
      u1: { lot: ["b"] },
    })
    toggleShortlisted("u1", "other", "c")
    expect(shortlistsOf("u1")).toEqual({ lot: ["b"], other: ["c"] })
    expect(shortlistsOf("u2")).toEqual({})
  })

  it("reads what an earlier session saved", () => {
    localStorage.setItem(SHORTLIST_KEY, JSON.stringify({ u9: { x: ["y"] } }))
    resetShortlists()
    expect(shortlistsOf("u9")).toEqual({ x: ["y"] })
  })
})

describe("the last upload", () => {
  it("is remembered between visits", () => {
    expect(readLastUpload()).toBeUndefined()
    rememberUpload("u1")
    expect(readLastUpload()).toBe("u1")
  })
})
