import { describe, expect, it, vi } from "vitest"
import { createHttpGateway, HTTP_MAX_NOTICES, UPLOADS_PATH } from "@/entities/upload/http"
import type { HttpClient } from "@/shared/api/http-client"
import { PayloadFormatError } from "@/shared/api/payload"
import { recommendationFixture } from "../recommendation/fixture"

const summary = {
  id: "u 1",
  fileName: "n.csv",
  createdAt: "2026-10-01",
  total: 2,
  processed: 1,
  counts: { ready: 1, needsCheck: 0, noCandidates: 0, failed: 0 },
  rejected: 1,
}
const lot = {
  id: "10",
  title: "Food",
  status: "ready",
  products: 5,
  candidates: 3,
  startPrice: 12.5,
}

function client(payload: unknown): HttpClient {
  const answer = vi.fn(async (_path: string, options: { parse: (value: unknown) => unknown }) =>
    options.parse(payload),
  )
  return { get: answer, post: answer } as unknown as HttpClient
}

describe("the http gateway", () => {
  it("lists, reads and creates uploads", async () => {
    const http = client({ uploads: [summary] })
    const gateway = createHttpGateway(http)
    expect(gateway.maxNotices).toBe(HTTP_MAX_NOTICES)
    expect(HTTP_MAX_NOTICES).toBe(5000)
    expect(await gateway.list()).toEqual([{ ...summary, stored: true }])
    expect(http.get).toHaveBeenCalledWith(UPLOADS_PATH, expect.anything())

    const detail = createHttpGateway(
      client({
        ...summary,
        lots: [
          lot,
          { id: "11", title: "Paper", status: "queued", products: 0, candidates: 0 },
          { id: "12", title: "Ink", status: "failed", products: 0, candidates: 0 },
        ],
        issues: [{ row: 3, code: "badPrice", value: "x" }],
      }),
    )
    const read = await detail.get("u 1")
    expect(read.lots[0]).toEqual(lot)
    expect(read.lots[2]?.status).toBe("failed")
    expect(read.issues).toEqual([{ row: 3, code: "badPrice", value: "x" }])

    const light = client(summary)
    expect(await createHttpGateway(light).summary?.("u 1")).toEqual({
      ...summary,
      stored: true,
    })
    expect(light.get).toHaveBeenCalledWith(`${UPLOADS_PATH}/u%201/summary`, expect.anything())

    const post = client(summary)
    const file = new File(["x"], "n.csv")
    await createHttpGateway(post).create({
      file,
      check: {
        ok: true,
        fileName: "n.csv",
        columns: [],
        preview: [],
        total: 0,
        notices: [],
        issues: [],
      },
    })
    const [path, options] = vi.mocked(post.post).mock.calls[0] ?? []
    expect(path).toBe(UPLOADS_PATH)
    expect(options?.body instanceof FormData && options.body.get("file")).toBeInstanceOf(File)
  })

  it("reads a lot with or without a recommendation and exports results", async () => {
    const http = client({ upload: summary, lot, recommendation: recommendationFixture })
    const detail = await createHttpGateway(http).lot("u 1", "10/a")
    expect(detail.recommendation?.companies).toHaveLength(3)
    expect(vi.mocked(http.get).mock.calls[0]?.[0]).toBe("/uploads/u%201/lots/10%2Fa")
    const pending = await createHttpGateway(
      client({ upload: summary, lot, recommendation: null }),
    ).lot("u", "10")
    expect(pending.recommendation).toBeUndefined()
    const results = client({ results: [{ lot, recommendation: recommendationFixture }] })
    expect(await createHttpGateway(results).results("u", ["10"])).toHaveLength(1)
    expect(vi.mocked(results.post).mock.calls[0]?.[1]).toMatchObject({
      body: { lotIds: ["10"] },
    })
  })

  it("rejects malformed answers", async () => {
    await expect(
      createHttpGateway(client({ uploads: [{ ...summary, total: -1 }] })).list(),
    ).rejects.toBeInstanceOf(PayloadFormatError)
    const { failed: _, ...withoutFailed } = summary.counts
    await expect(
      createHttpGateway(client({ uploads: [{ ...summary, counts: withoutFailed }] })).list(),
    ).rejects.toThrow("$.uploads[0].counts.failed")
    await expect(
      createHttpGateway(
        client({ ...summary, lots: [{ ...lot, startPrice: "1" }], issues: [] }),
      ).get("u"),
    ).rejects.toThrow("$.lots[0].startPrice")
  })
})
