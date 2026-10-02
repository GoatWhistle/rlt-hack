import type { SearchSummary } from "@/entities/search/model"

export type HistoryAge = {
  readonly unit: "day" | "week" | "month" | "year"
  readonly value: number
}

export type HistoryGroup = {
  readonly key: string
  readonly age: HistoryAge
  readonly searches: readonly SearchSummary[]
}

const DAY_MS = 86_400_000
const WEEK = 7
const MONTH_DAYS = 30
const YEAR_MONTHS = 12

function dayStart(date: Date): number {
  return Date.UTC(date.getFullYear(), date.getMonth(), date.getDate())
}

export function ageOf(iso: string, now: Date = new Date()): HistoryAge {
  const date = new Date(iso)
  const days = Math.max(0, Math.round((dayStart(now) - dayStart(date)) / DAY_MS))
  if (days < WEEK) return { unit: "day", value: -days }
  if (days < MONTH_DAYS) return { unit: "week", value: -Math.floor(days / WEEK) }
  const months =
    now.getFullYear() * YEAR_MONTHS +
    now.getMonth() -
    (date.getFullYear() * YEAR_MONTHS + date.getMonth())
  if (months < YEAR_MONTHS) return { unit: "month", value: -Math.max(1, months) }
  return { unit: "year", value: -(now.getFullYear() - date.getFullYear()) }
}

export function isRecentDay(age: HistoryAge): boolean {
  return age.unit === "day" && age.value >= -1
}

export function groupHistory(
  searches: readonly SearchSummary[],
  now: Date = new Date(),
): HistoryGroup[] {
  const groups: { key: string; age: HistoryAge; searches: SearchSummary[] }[] = []
  for (const search of searches) {
    const age = ageOf(search.createdAt, now)
    const key = `${age.unit}:${age.value}`
    const last = groups.at(-1)
    if (last && last.key === key) last.searches.push(search)
    else groups.push({ key, age, searches: [search] })
  }
  return groups
}
