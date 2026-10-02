import { type Candidate, matchOf, type QueryItem } from "./model"

export const CELL_STATES = [
  "offer",
  "registered",
  "assumed",
  "history",
  "conflict",
  "insufficient",
] as const
export type CellState = (typeof CELL_STATES)[number]

const REGISTERED = new Set(["registry", "dataset"])

export function cellState(candidate: Candidate, itemId: string): CellState {
  const match = matchOf(candidate, itemId)
  if (match) {
    if (match.checks.some((check) => check.status === "conflict")) return "conflict"
    if (match.offer && REGISTERED.has(match.offer.sourceType)) return "registered"
    if (match.basis === "stock" || match.basis === "catalog") return "offer"
    return "assumed"
  }
  const inHistory = candidate.history.records.some((record) => record.itemIds.includes(itemId))
  return inHistory ? "history" : "insufficient"
}

export type CoverageSummary = {
  readonly confirmed: number
  readonly toClarify: number
  readonly missing: number
  readonly total: number
}

export function confirmedCell(candidate: Candidate, itemId: string): boolean {
  const state = cellState(candidate, itemId)
  if (state !== "offer" && state !== "registered") return false
  const checks = matchOf(candidate, itemId)?.checks ?? []
  return checks.every((check) => check.status === "met")
}

export function coverageOf(candidate: Candidate, items: readonly QueryItem[]): CoverageSummary {
  let confirmed = 0
  let toClarify = 0
  for (const item of items) {
    const state = cellState(candidate, item.id)
    if (confirmedCell(candidate, item.id)) confirmed += 1
    else if (state !== "insufficient" && state !== "conflict") toClarify += 1
  }
  return {
    confirmed,
    toClarify,
    missing: items.length - confirmed - toClarify,
    total: items.length,
  }
}
