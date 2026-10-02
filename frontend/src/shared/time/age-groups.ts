export type Age = {
  readonly unit: "day" | "week" | "month" | "year"
  readonly value: number
}

export type AgeGroup<T> = {
  readonly key: string
  readonly age: Age
  readonly items: readonly T[]
}

const DAY_MS = 86_400_000
const WEEK = 7
const MONTH_DAYS = 30
const YEAR_MONTHS = 12

function dayStart(date: Date): number {
  return Date.UTC(date.getFullYear(), date.getMonth(), date.getDate())
}

export function ageOf(iso: string, now: Date = new Date()): Age {
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

export function isRecentDay(age: Age): boolean {
  return age.unit === "day" && age.value >= -1
}

export function groupByAge<T extends { readonly createdAt: string }>(
  items: readonly T[],
  now: Date = new Date(),
): AgeGroup<T>[] {
  const groups: { key: string; age: Age; items: T[] }[] = []
  for (const item of items) {
    const age = ageOf(item.createdAt, now)
    const key = `${age.unit}:${age.value}`
    const last = groups.at(-1)
    if (last && last.key === key) last.items.push(item)
    else groups.push({ key, age, items: [item] })
  }
  return groups
}
