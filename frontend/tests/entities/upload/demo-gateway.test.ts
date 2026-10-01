import { describe, expect, it } from "vitest"
import type { CheckedFile, Notice } from "@/entities/notice/model"
import {
  createDemoGateway,
  DEMO_MAX_NOTICES,
  MAX_PROCESSING_MS,
  MIN_PROCESSING_MS,
  MS_PER_LOT,
  processedCount,
} from "@/entities/upload/demo/gateway"
import { demoRecommendation, variantOf } from "@/entities/upload/demo/result"
import { createUploadStore, UPLOADS_KEY } from "@/entities/upload/demo/store"
import { statusOf } from "@/entities/upload/model"
import type { JsonStorage } from "@/shared/storage/local-json"

function notices(count: number): Notice[] {
  return Array.from({ length: count }, (_, index) => ({
    lotId: String(1000 + index),
    title: `Purchase ${index}`,
    ...(index === 0
      ? {
          subject: "Food",
          customerInn: "7800000001",
          publishDate: "2025-01-02",
          startPrice: 10,
        }
      : {}),
  }))
}

function checked(count: number): CheckedFile {
  return {
    ok: true,
    fileName: "n.csv",
    columns: [],
    preview: [],
    total: count + 1,
    notices: notices(count),
    issues: [{ row: 9, code: "badPrice", value: "x" }],
  }
}

function memoryStorage(writable = true): JsonStorage & { data: Map<string, unknown> } {
  const data = new Map<string, unknown>()
  return {
    data,
    read: (key) => data.get(key),
    write: (key, value) => {
      if (!writable) return false
      data.set(key, value)
      return true
    },
  }
}

describe("processedCount", () => {
  it("advances with time inside the bounds", () => {
    expect(processedCount(10, 0, 0)).toBe(0)
    expect(processedCount(10, 0, MS_PER_LOT * 5)).toBe(5)
    expect(processedCount(2, 0, MIN_PROCESSING_MS / 2)).toBe(1)
    expect(processedCount(10, 0, MAX_PROCESSING_MS)).toBe(10)
    expect(processedCount(10_000, 0, MAX_PROCESSING_MS / 2)).toBe(5000)
    expect(processedCount(4, 100, 0)).toBe(0)
  })
})

describe("the demo gateway", () => {
  it("stores an upload and reveals results as processing goes", async () => {
    let now = 0
    const storage = memoryStorage()
    const gateway = createDemoGateway({
      store: createUploadStore(storage),
      now: () => now,
      newId: () => "u1",
    })
    expect(gateway.demo).toBe(true)
    expect(gateway.maxNotices).toBe(DEMO_MAX_NOTICES)
    const created = await gateway.create({ file: new File([""], "n.csv"), check: checked(10) })
    expect(created).toMatchObject({
      id: "u1",
      total: 10,
      processed: 0,
      rejected: 1,
      stored: true,
    })
    expect(storage.data.get(UPLOADS_KEY)).toHaveLength(1)

    now = MS_PER_LOT * 5
    const half = await gateway.get("u1")
    expect(half.processed).toBe(5)
    expect(half.lots[0]).toMatchObject({ id: "1000", subject: "Food", startPrice: 10 })
    expect(half.lots[9]).toMatchObject({ status: "queued", products: 0, candidates: 0 })
    expect(half.issues).toHaveLength(1)

    const queued = await gateway.lot("u1", "1009")
    expect(queued.recommendation).toBeUndefined()
    const ready = await gateway.lot("u1", "1000")
    expect(ready.recommendation?.requestTitle).toBe("Purchase 0")
    expect(ready.upload.processed).toBe(5)

    const results = await gateway.results("u1", ["1000", "1009", "nope"])
    expect(results.map((result) => result.lot.id)).toEqual(["1000"])

    now = MAX_PROCESSING_MS
    const [summary] = await gateway.list()
    expect(summary?.processed).toBe(10)
    const counts = summary?.counts
    expect((counts?.ready ?? 0) + (counts?.needsCheck ?? 0) + (counts?.noCandidates ?? 0)).toBe(
      10,
    )
  })

  it("answers unknown uploads and lots with 404", async () => {
    const gateway = createDemoGateway({ store: createUploadStore(memoryStorage()) })
    await expect(gateway.get("x")).rejects.toMatchObject({ status: 404 })
    await gateway.create({ file: new File([""], "n.csv"), check: checked(1) })
    const [upload] = await gateway.list()
    await expect(gateway.lot(upload?.id ?? "", "nope")).rejects.toMatchObject({ status: 404 })
  })

  it("keeps an upload in memory when the browser storage is full", async () => {
    const store = createUploadStore(memoryStorage(false))
    const gateway = createDemoGateway({ store, newId: () => "big" })
    const created = await gateway.create({ file: new File([""], "n.csv"), check: checked(1) })
    expect(created.stored).toBe(false)
    expect(store.find("big")).toBeDefined()
  })

  it("restores saved uploads and skips malformed entries", () => {
    const storage = memoryStorage()
    storage.data.set(UPLOADS_KEY, [
      { id: "a", fileName: "a.csv", createdAt: "x", startedAt: 0, notices: [], issues: [] },
      { id: "b" },
      null,
    ])
    expect(
      createUploadStore(storage)
        .all()
        .map((upload) => upload.id),
    ).toEqual(["a"])
    const broken = memoryStorage()
    broken.data.set(UPLOADS_KEY, "nope")
    expect(createUploadStore(broken).all()).toEqual([])
  })
})

describe("demo results", () => {
  it("varies by lot: no candidates, assumptions to confirm or ready", () => {
    const ids = Array.from({ length: 40 }, (_, index) => String(5000 + index))
    const statuses = new Set(
      ids.map((lotId) => statusOf(demoRecommendation({ lotId, title: "T" }, "f.csv"))),
    )
    expect(statuses).toEqual(new Set(["ready", "needsCheck", "noCandidates"]))
    const ready = ids.find((lotId) => variantOf(lotId) > 4) ?? ""
    const recommendation = demoRecommendation({ lotId: ready, title: "Title" }, "f.csv")
    expect(recommendation.products.some((product) => product.origin === "inferred")).toBe(false)
    expect(recommendation).toMatchObject({
      fileName: "f.csv",
      requestTitle: "Title",
      lotLabel: ready,
    })
  })
})
