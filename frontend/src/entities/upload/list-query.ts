import { LOCALE_TAGS, type Locale } from "@/shared/i18n/locale"
import type { LotStatus, LotSummary, ResultStatus } from "./model"

export const PAGE_SIZE = 20
export const FILTERS = ["all", "ready", "needsCheck", "noCandidates"] as const
export type Filter = (typeof FILTERS)[number]

export type ListQuery = {
  readonly search: string
  readonly filter: Filter
  readonly page: number
}

export function readQuery(params: URLSearchParams): ListQuery {
  const status = params.get("status")
  const page = Number(params.get("page"))
  return {
    search: params.get("q") ?? "",
    filter: FILTERS.find((filter) => filter === status) ?? "all",
    page: Number.isInteger(page) && page > 0 ? page : 1,
  }
}

export function writeQuery(query: ListQuery): string {
  const params = new URLSearchParams()
  if (query.search) params.set("q", query.search)
  if (query.filter !== "all") params.set("status", query.filter)
  if (query.page > 1) params.set("page", String(query.page))
  const search = params.toString()
  return search ? `?${search}` : ""
}

function matchesSearch(lot: LotSummary, search: string, tag: string): boolean {
  const needle = search.trim().toLocaleLowerCase(tag)
  if (!needle) return true
  return [lot.title, lot.subject, lot.customerInn, lot.id].some((value) =>
    value?.toLocaleLowerCase(tag).includes(needle),
  )
}

function matchesFilter(status: LotStatus, filter: Filter): boolean {
  return filter === "all" || status === filter
}

export function searched(
  lots: readonly LotSummary[],
  search: string,
  locale: Locale,
): LotSummary[] {
  const tag = LOCALE_TAGS[locale]
  return lots.filter((lot) => matchesSearch(lot, search, tag))
}

export function filtered(
  lots: readonly LotSummary[],
  query: ListQuery,
  locale: Locale,
): LotSummary[] {
  return searched(lots, query.search, locale).filter((lot) =>
    matchesFilter(lot.status, query.filter),
  )
}

export function filterCounts(lots: readonly LotSummary[]): Record<Filter, number> {
  const count = (status: ResultStatus) => lots.filter((lot) => lot.status === status).length
  return {
    all: lots.length,
    ready: count("ready"),
    needsCheck: count("needsCheck"),
    noCandidates: count("noCandidates"),
  }
}

export function pageCount(total: number): number {
  return Math.max(1, Math.ceil(total / PAGE_SIZE))
}

export function pageOf<T>(items: readonly T[], page: number): T[] {
  const last = pageCount(items.length)
  const current = Math.min(page, last)
  return items.slice((current - 1) * PAGE_SIZE, current * PAGE_SIZE)
}

export function pageForIndex(index: number): number {
  return Math.floor(Math.max(0, index) / PAGE_SIZE) + 1
}
