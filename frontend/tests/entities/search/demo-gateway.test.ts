import { instant } from "@tests/support/search"
import { describe, expect, it, vi } from "vitest"
import {
  DEMO_PIPELINE,
  demoPayload,
  pickScenario,
  SCENARIOS,
} from "@/entities/search/demo/catalog"
import { fallbackItems } from "@/entities/search/demo/fallback"
import { createDemoSearchGateway, SEARCH_DELAY_MS } from "@/entities/search/demo/gateway"
import { localize } from "@/entities/search/demo/localize"
import { createSearchStore, SEARCHES_KEY, STORED_SEARCHES } from "@/entities/search/demo/store"
import { parseSearchResult } from "@/entities/search/parse"
import { isApiError } from "@/shared/api/api-error"
import type { Locale } from "@/shared/i18n/locale"
import { createJsonStorage, type JsonStorage } from "@/shared/storage/local-json"

function memory(): JsonStorage & { readonly saved: Map<string, unknown> } {
  const saved = new Map<string, unknown>()
  return {
    saved,
    read: (key) => saved.get(key),
    write: (key, value) => {
      saved.set(key, value)
      return true
    },
  }
}

function gateway(locale: Locale = "en", storage: JsonStorage = memory()) {
  let id = 0
  return createDemoSearchGateway({
    store: createSearchStore(storage),
    wait: instant,
    locale: () => locale,
    now: () => Date.parse("2026-10-01T12:00:00Z"),
    newId: () => `s${++id}`,
  })
}

async function codeOf(promise: Promise<unknown>): Promise<string> {
  try {
    await promise
  } catch (error) {
    return isApiError(error) ? error.code : "other"
  }
  return "none"
}

describe("the demo search", () => {
  it("answers every scenario in both languages with a payload the contract accepts", () => {
    for (const scenario of SCENARIOS) {
      for (const locale of ["ru", "en"] as const) {
        const stored = {
          searchId: "x",
          text: "t",
          scenario: scenario.id,
          createdAt: "2026-10-01",
        }
        const result = parseSearchResult(demoPayload(stored, locale))
        expect(result.candidates.length).toBeGreaterThan(0)
        expect(result.pipeline.version).toBe(DEMO_PIPELINE.version)
        expect(JSON.stringify(result)).not.toMatch(/"(ru|en)":/)
      }
    }
  })

  it("picks a scenario by the words of the query", () => {
    expect(pickScenario("Крупа гречневая 500 кг")).toBe("groats")
    expect(pickScenario("office paper and pens")).toBe("office")
    expect(pickScenario("nitrile gloves")).toBe("medical")
    expect(pickScenario("tractor tyres")).toBeNull()
  })

  it("finds candidates, keeps the search and reads it back in the current language", async () => {
    const storage = memory()
    const english = gateway("en", storage)
    const found = await english.search({ text: "  buckwheat and rice  " })
    expect(found.searchId).toBe("s1")
    expect(found.query.text).toBe("buckwheat and rice")
    expect(found.candidates.some((candidate) => candidate.status === "check")).toBe(true)
    expect(found.candidates[0]?.name).toBe("Severny Proviant LLC")
    const russian = gateway("ru", storage)
    const again = await russian.get("s1")
    expect(again.candidates[0]?.name).toContain("Северный Провиант")
    expect(await russian.recent(5)).toEqual([
      expect.objectContaining({ searchId: "s1", items: 2, candidates: 4, recommended: 2 }),
    ])
  })

  it("reports a warning and an assumed item", async () => {
    const found = await gateway().search({ text: "paper for the office" })
    expect(found.warnings).toEqual([{ code: "itemsInferred", subject: "" }])
    expect(found.items.some((item) => item.origin === "inferred")).toBe(true)
  })

  it("returns no candidates for an unknown request but keeps its items", async () => {
    const found = await gateway().search({ text: "tractor tyres 4 pcs; engine oil" })
    expect(found.candidates).toEqual([])
    expect(found.items.map((item) => item.name)).toEqual(["tractor tyres", "engine oil"])
    expect(found.items[0]?.quantity).toEqual({ value: "4", unit: "pcs" })
  })

  it("rejects empty, long and meaningless text and unknown searches", async () => {
    const demo = gateway()
    expect(await codeOf(demo.search({ text: "   " }))).toBe("empty_query")
    expect(await codeOf(demo.search({ text: "a".repeat(4001) }))).toBe("query_too_long")
    expect(await codeOf(demo.search({ text: "123 !!!" }))).toBe("query_not_understood")
    expect(await codeOf(demo.get("missing"))).toBe("search_not_found")
  })

  it("waits a little before answering", async () => {
    vi.useFakeTimers()
    const demo = createDemoSearchGateway({ store: createSearchStore(memory()) })
    let done = false
    void demo.search({ text: "rice" }).then(() => {
      done = true
    })
    await vi.advanceTimersByTimeAsync(SEARCH_DELAY_MS - 1)
    expect(done).toBe(false)
    await vi.advanceTimersByTimeAsync(1)
    expect(done).toBe(true)
  })
})

describe("the demo search store", () => {
  it("keeps the latest searches and ignores broken entries", () => {
    const storage = memory()
    storage.saved.set(SEARCHES_KEY, [{ searchId: 1 }, null, "x"])
    const store = createSearchStore(storage)
    expect(store.all()).toEqual([])
    for (let index = 0; index <= STORED_SEARCHES; index += 1) {
      store.add({ searchId: `s${index}`, text: "t", scenario: null, createdAt: "2026" })
    }
    expect(store.all()).toHaveLength(STORED_SEARCHES)
    expect(store.find("s0")).toBeUndefined()
    expect(createSearchStore(storage).find(`s${STORED_SEARCHES}`)).toBeDefined()
    expect(createSearchStore(createJsonStorage(() => localStorage)).all()).toEqual([])
  })
})

describe("demo helpers", () => {
  it("split free text into items and read a trailing quantity", () => {
    expect(fallbackItems("bolts M8 200,5 kg;\n\n washers")).toEqual([
      {
        id: "i1",
        name: "bolts M8",
        okpd2: "",
        itemType: "unknown",
        origin: "text",
        quantity: { value: "200.5", unit: "kg" },
      },
      expect.objectContaining({ id: "i2", name: "washers", quantity: null }),
    ])
    expect(fallbackItems("boxes 10")[0]?.quantity).toEqual({ value: "10", unit: "" })
  })

  it("localize nested prose and leave other values alone", () => {
    expect(localize({ a: [{ ru: "да", en: "yes" }], b: 1, c: null }, "en")).toEqual({
      a: ["yes"],
      b: 1,
      c: null,
    })
  })
})
