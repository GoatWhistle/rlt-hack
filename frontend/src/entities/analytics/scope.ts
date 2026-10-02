import { ANALYTICS_RECORDS_PATH } from "@/shared/config/paths"
import {
  type AnalyticsFilters,
  RECORD_PROBLEMS,
  type RecordProblem,
  SOURCE_TYPES,
} from "./model"

export const RECORDS_PAGE_SIZE = 25

export function readFilters(params: URLSearchParams): AnalyticsFilters {
  const type = params.get("type")
  const sourceType = SOURCE_TYPES.find((option) => option === type)
  const sourceId = params.get("source") || undefined
  const region = params.get("region")?.trim() || undefined
  return {
    ...(sourceId ? { sourceId } : {}),
    ...(sourceType ? { sourceType } : {}),
    ...(region ? { region } : {}),
  }
}

export function writeFilters(filters: AnalyticsFilters, extra?: URLSearchParams): string {
  const params = new URLSearchParams(extra)
  params.delete("source")
  params.delete("type")
  params.delete("region")
  if (filters.sourceId) params.set("source", filters.sourceId)
  if (filters.sourceType) params.set("type", filters.sourceType)
  if (filters.region) params.set("region", filters.region)
  const search = params.toString()
  return search ? `?${search}` : ""
}

export function hasFilters(filters: AnalyticsFilters): boolean {
  return Boolean(filters.sourceId || filters.sourceType || filters.region)
}

export function readProblem(params: URLSearchParams): RecordProblem | undefined {
  const value = params.get("problem")
  return RECORD_PROBLEMS.find((option) => option === value)
}

export function readOffset(params: URLSearchParams): number {
  const page = Number(params.get("page"))
  return Number.isInteger(page) && page > 1 ? (page - 1) * RECORDS_PAGE_SIZE : 0
}

export function recordsHref(
  filters: AnalyticsFilters,
  extra: { readonly problem?: RecordProblem; readonly category?: string } = {},
): string {
  const params = new URLSearchParams()
  if (extra.problem) params.set("problem", extra.problem)
  if (extra.category) params.set("category", extra.category)
  return `${ANALYTICS_RECORDS_PATH}${writeFilters(filters, params)}`
}
