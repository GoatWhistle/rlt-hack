import type { Notice } from "@/entities/notice/model"
import { type NewUpload, notFound, type UploadGateway } from "../gateway"
import {
  type LotDetail,
  type LotResult,
  type LotSummary,
  RESULT_STATUSES,
  statusOf,
  type UploadDetail,
  type UploadSummary,
} from "../model"
import { demoRecommendation } from "./result"
import { createUploadStore, type StoredUpload, type UploadStore } from "./store"

export const DEMO_MAX_NOTICES = 5000
export const MS_PER_LOT = 350
export const MIN_PROCESSING_MS = 2000
export const MAX_PROCESSING_MS = 15_000

export function processedCount(total: number, startedAt: number, now: number): number {
  const duration = Math.min(MAX_PROCESSING_MS, Math.max(MIN_PROCESSING_MS, total * MS_PER_LOT))
  const share = Math.max(0, now - startedAt) / duration
  return Math.min(total, Math.floor(total * share))
}

export type DemoGatewayOptions = {
  readonly store?: UploadStore
  readonly now?: () => number
  readonly newId?: () => string
}

function lotSummary(notice: Notice, result?: LotResult["recommendation"]): LotSummary {
  return {
    id: notice.lotId,
    title: notice.title,
    ...(notice.subject ? { subject: notice.subject } : {}),
    ...(notice.customerInn ? { customerInn: notice.customerInn } : {}),
    ...(notice.publishDate ? { publishDate: notice.publishDate } : {}),
    ...(notice.startPrice === undefined ? {} : { startPrice: notice.startPrice }),
    status: result ? statusOf(result) : "queued",
    products: result?.products.length ?? 0,
    candidates: result?.companies.length ?? 0,
  }
}

export function createDemoGateway(options: DemoGatewayOptions = {}): UploadGateway {
  const store = options.store ?? createUploadStore()
  const now = options.now ?? Date.now
  const newId = options.newId ?? (() => crypto.randomUUID())

  function results(upload: StoredUpload): LotResult[] {
    const processed = processedCount(upload.notices.length, upload.startedAt, now())
    return upload.notices.map((notice, index) => {
      const recommendation =
        index < processed ? demoRecommendation(notice, upload.fileName) : undefined
      return recommendation
        ? { lot: lotSummary(notice, recommendation), recommendation }
        : { lot: lotSummary(notice) }
    })
  }

  function summarize(upload: StoredUpload, lots: readonly LotSummary[]): UploadSummary {
    const count = (status: LotSummary["status"]) =>
      lots.filter((lot) => lot.status === status).length
    return {
      id: upload.id,
      fileName: upload.fileName,
      createdAt: upload.createdAt,
      total: lots.length,
      processed: lots.length - count("queued"),
      counts: Object.fromEntries(RESULT_STATUSES.map((status) => [status, count(status)])) as {
        [K in (typeof RESULT_STATUSES)[number]]: number
      },
      rejected: upload.issues.length === 0 ? 0 : new Set(upload.issues.map((i) => i.row)).size,
      stored: store.isStored(upload.id),
    }
  }

  function find(uploadId: string): StoredUpload {
    const upload = store.find(uploadId)
    if (!upload) throw notFound()
    return upload
  }

  function lotsOf(upload: StoredUpload): LotSummary[] {
    return results(upload).map((result) => result.lot)
  }

  function detail(upload: StoredUpload): UploadDetail {
    const lots = lotsOf(upload)
    return { ...summarize(upload, lots), lots, issues: upload.issues }
  }

  return {
    demo: true,
    maxNotices: DEMO_MAX_NOTICES,
    list: async () => store.all().map((upload) => summarize(upload, lotsOf(upload))),
    get: async (uploadId) => detail(find(uploadId)),
    create: async ({ file, check }: NewUpload) => {
      const upload: StoredUpload = {
        id: newId(),
        fileName: file.name,
        createdAt: new Date(now()).toISOString(),
        startedAt: now(),
        notices: check.notices,
        issues: check.issues,
      }
      store.add(upload)
      return summarize(upload, lotsOf(upload))
    },
    lot: async (uploadId, lotId): Promise<LotDetail> => {
      const upload = find(uploadId)
      const all = results(upload)
      const found = all.find((result) => result.lot.id === lotId)
      if (!found) throw notFound()
      return {
        ...found,
        upload: summarize(
          upload,
          all.map((result) => result.lot),
        ),
      }
    },
    results: async (uploadId, lotIds) => {
      const wanted = new Set(lotIds)
      return results(find(uploadId)).filter(
        (result) => wanted.has(result.lot.id) && result.recommendation,
      )
    },
  }
}
