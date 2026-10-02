import { describe, expect, it, vi } from "vitest"
import { createHttpAnalyticsGateway } from "@/entities/analytics/gateway"
import { parseOverview, parseRecords } from "@/entities/analytics/parse-report"
import type { HttpClient } from "@/shared/api/http-client"
import { PayloadFormatError } from "@/shared/api/payload"

const ratio = { numerator: 1, denominator: 2, unknown: 0, share: 0.5 }
const meta = {
  snapshotId: "s",
  asOf: "2026-10-02T09:00:00Z",
  computedAt: "2026-10-02T09:00:00Z",
  definitionsVersion: "v1",
  delaySeconds: 0,
  warnings: [],
  filters: {},
  policy: { offerDays: 7, registryDays: 30, periodDays: 30, version: "d" },
}
const source = {
  sourceId: "a",
  name: "A",
  providerName: "a",
  sourceType: "feed",
  state: "ok",
  offers: 1,
  companies: 1,
  fresh: ratio,
  lastSuccessAt: "2026-10-01T00:00:00Z",
  runs: 1,
  failedRuns: 0,
}
const run = {
  runId: "r",
  sourceId: "a",
  sourceName: "A",
  startedAt: "2026-10-01T00:00:00Z",
  finishedAt: "2026-10-01T00:01:00Z",
  durationSeconds: 60,
  status: "success",
  suppliersExtracted: 1,
  offersExtracted: 1,
  errorMessage: "",
}

function client(answers: Record<string, unknown>) {
  const get = vi.fn(async (path: string, options: { parse: (value: unknown) => unknown }) =>
    options.parse(answers[path]),
  )
  return { http: { get, post: get } as unknown as HttpClient, get }
}

describe("the analytics gateway", () => {
  it("combines sources and runs and sends the filters", async () => {
    const { http, get } = client({
      "/analytics/sources": { meta, items: [source] },
      "/analytics/runs": { meta, success: ratio, partial: 1, items: [run] },
    })
    const report = await createHttpAnalyticsGateway(http).sources({ sourceType: "feed" })
    expect(report.items[0]?.name).toBe("A")
    expect(report.runs[0]?.status).toBe("success")
    expect(report.partial).toBe(1)
    expect(get.mock.calls[0]?.[1]).toMatchObject({ query: { sourceType: "feed" } })
  })

  it("parses an overview and rejects a ratio without a share", () => {
    const body = {
      meta,
      offers: 1,
      companies: 1,
      composition: [{ key: "feed", count: 1 }],
      fresh: ratio,
      searchable: ratio,
      runsSuccess: { ...ratio, denominator: 0, share: null },
      runsPartial: 0,
      attention: [{ code: "no_category", count: 1, total: 2 }],
      categories: [],
      sources: [source],
      runs: [run],
    }
    expect(parseOverview(body).runsSuccess.share).toBeNull()
    expect(() => parseOverview({ ...body, fresh: { ...ratio, share: "x" } })).toThrow(
      PayloadFormatError,
    )
    expect(() => parseOverview({ ...body, sources: [{ ...source, state: "?" }] })).toThrow(
      PayloadFormatError,
    )
  })

  it("passes the record query and keeps an absent price absent", async () => {
    const page = {
      asOf: meta.asOf,
      total: 1,
      changedAfter: 0,
      items: [
        {
          offerId: "o",
          name: "N",
          sourceName: "A",
          supplierName: "",
          okpd2Code: "",
          price: null,
          currency: "",
          url: "u",
          lastSeenAt: meta.asOf,
        },
      ],
    }
    const { http, get } = client({ "/analytics/records": page })
    const result = await createHttpAnalyticsGateway(http).records(
      { region: "78" },
      { problem: "stale", offset: 25, limit: 25 },
    )
    expect(result.items[0]).not.toHaveProperty("price")
    expect(get.mock.calls[0]?.[1]).toMatchObject({
      query: { region: "78", problem: "stale", offset: 25, limit: 25 },
    })
    expect(parseRecords(page).total).toBe(1)
  })
})
