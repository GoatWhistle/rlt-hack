import { ISSUE_CODES, type RowIssue } from "@/entities/notice/model"
import { parseRecommendation } from "@/entities/recommendation/parse"
import {
  count,
  list,
  oneOf,
  optionalAmount,
  optionalText,
  record,
  text,
  withOptional,
} from "@/shared/api/payload"
import {
  LOT_STATUSES,
  type LotDetail,
  type LotResult,
  type LotSummary,
  type UploadDetail,
  type UploadSummary,
} from "./model"

function issue(value: unknown, path: string): RowIssue {
  const fields = record(value, path)
  return withOptional(
    { row: count(fields, "row", path), code: oneOf(ISSUE_CODES, fields, "code", path) },
    { value: optionalText(fields, "value", path) },
  )
}

function lot(value: unknown, path: string): LotSummary {
  const fields = record(value, path)
  return withOptional(
    {
      id: text(fields, "id", path),
      title: text(fields, "title", path),
      status: oneOf(LOT_STATUSES, fields, "status", path),
      products: count(fields, "products", path),
      candidates: count(fields, "candidates", path),
    },
    {
      subject: optionalText(fields, "subject", path),
      customerInn: optionalText(fields, "customerInn", path),
      publishDate: optionalText(fields, "publishDate", path),
      startPrice: optionalAmount(fields, "startPrice", path),
    },
  )
}

export function parseUploadSummary(value: unknown, path = "$"): UploadSummary {
  const fields = record(value, path)
  const counts = record(fields.counts, `${path}.counts`)
  return {
    id: text(fields, "id", path),
    fileName: text(fields, "fileName", path),
    createdAt: text(fields, "createdAt", path),
    total: count(fields, "total", path),
    processed: count(fields, "processed", path),
    counts: {
      ready: count(counts, "ready", `${path}.counts`),
      needsCheck: count(counts, "needsCheck", `${path}.counts`),
      noCandidates: count(counts, "noCandidates", `${path}.counts`),
      failed: count(counts, "failed", `${path}.counts`),
    },
    rejected: count(fields, "rejected", path),
    stored: true,
  }
}

export function parseUploadList(value: unknown): UploadSummary[] {
  return list(record(value, "$"), "uploads", "$", parseUploadSummary)
}

export function parseUploadDetail(value: unknown): UploadDetail {
  const fields = record(value, "$")
  return {
    ...parseUploadSummary(value),
    lots: list(fields, "lots", "$", lot),
    issues: list(fields, "issues", "$", issue),
  }
}

function lotResult(value: unknown, path: string): LotResult {
  const fields = record(value, path)
  const recommendation =
    fields.recommendation === undefined || fields.recommendation === null
      ? undefined
      : parseRecommendation(fields.recommendation)
  return { lot: lot(fields.lot, `${path}.lot`), ...(recommendation ? { recommendation } : {}) }
}

export function parseLotDetail(value: unknown): LotDetail {
  const fields = record(value, "$")
  return { ...lotResult(value, "$"), upload: parseUploadSummary(fields.upload, "$.upload") }
}

export function parseLotResults(value: unknown): LotResult[] {
  return list(record(value, "$"), "results", "$", lotResult)
}
