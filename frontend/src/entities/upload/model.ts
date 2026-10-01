import { DEGRADING_WARNINGS } from "@/entities/evidence/model"
import type { RowIssue } from "@/entities/notice/model"
import type { Recommendation } from "@/entities/recommendation/model"

export const LOT_STATUSES = ["queued", "ready", "needsCheck", "noCandidates", "failed"] as const
export type LotStatus = (typeof LOT_STATUSES)[number]

export const RESULT_STATUSES = ["ready", "needsCheck", "noCandidates", "failed"] as const
export type ResultStatus = (typeof RESULT_STATUSES)[number]

export type LotSummary = {
  readonly id: string
  readonly title: string
  readonly subject?: string
  readonly customerInn?: string
  readonly publishDate?: string
  readonly startPrice?: number
  readonly status: LotStatus
  readonly products: number
  readonly candidates: number
}

export type UploadSummary = {
  readonly id: string
  readonly fileName: string
  readonly createdAt: string
  readonly total: number
  readonly processed: number
  readonly counts: Readonly<Record<ResultStatus, number>>
  readonly rejected: number
  readonly stored: boolean
}

export type UploadDetail = UploadSummary & {
  readonly lots: readonly LotSummary[]
  readonly issues: readonly RowIssue[]
}

export type LotResult = {
  readonly lot: LotSummary
  readonly recommendation?: Recommendation
}

export type LotDetail = LotResult & {
  readonly upload: UploadSummary
}

export function isProcessing(upload: UploadSummary): boolean {
  return upload.processed < upload.total
}

export function statusOf(recommendation: Recommendation): ResultStatus {
  if (recommendation.companies.length === 0) return "noCandidates"
  const assumed = recommendation.products.some((product) => product.origin === "inferred")
  const leaderToCheck = recommendation.companies[0]?.status === "check"
  const degraded = (recommendation.warnings ?? []).some((warning) =>
    DEGRADING_WARNINGS.includes(warning.code),
  )
  return assumed || leaderToCheck || degraded ? "needsCheck" : "ready"
}
