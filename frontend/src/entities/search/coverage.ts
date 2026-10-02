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

export type CoverPick = {
  readonly candidate: Candidate
  readonly confirmed: readonly string[]
  readonly toClarify: readonly string[]
}

export type CoverSet = {
  readonly picks: readonly CoverPick[]
  readonly gaps: readonly string[]
  readonly overlaps: readonly string[]
}

const COVER_LIMIT = 3

function reach(candidate: Candidate, itemIds: readonly string[]): CoverPick {
  const confirmed = itemIds.filter((id) => confirmedCell(candidate, id))
  const toClarify = itemIds.filter((id) => {
    const state = cellState(candidate, id)
    return !confirmed.includes(id) && state !== "insufficient" && state !== "conflict"
  })
  return { candidate, confirmed, toClarify }
}

function gain(pick: CoverPick, open: ReadonlySet<string>): [number, number] {
  return [
    pick.confirmed.filter((id) => open.has(id)).length,
    pick.toClarify.filter((id) => open.has(id)).length,
  ]
}

function better(value: [number, number], best: [number, number]): boolean {
  return value[0] > best[0] || (value[0] === best[0] && value[1] > best[1])
}

function nextPick(
  candidates: readonly Candidate[],
  ids: readonly string[],
  open: ReadonlySet<string>,
  taken: ReadonlySet<string>,
): CoverPick | undefined {
  let best: CoverPick | undefined
  let bestGain: [number, number] = [0, 0]
  for (const candidate of candidates.filter((entry) => !taken.has(entry.id))) {
    const pick = reach(candidate, ids)
    const value = gain(pick, open)
    if (better(value, bestGain)) {
      best = pick
      bestGain = value
    }
  }
  return best
}

export function coverSet(
  candidates: readonly Candidate[],
  items: readonly QueryItem[],
): CoverSet {
  const ids = items.map((item) => item.id)
  const open = new Set(ids)
  const taken = new Set<string>()
  const picks: CoverPick[] = []
  const covered = new Map<string, number>()
  while (open.size > 0 && picks.length < COVER_LIMIT) {
    const best = nextPick(candidates, ids, open, taken)
    if (!best) break
    picks.push(best)
    taken.add(best.candidate.id)
    for (const id of [...best.confirmed, ...best.toClarify]) {
      covered.set(id, (covered.get(id) ?? 0) + 1)
      open.delete(id)
    }
  }
  return {
    picks,
    gaps: ids.filter((id) => open.has(id)),
    overlaps: ids.filter((id) => (covered.get(id) ?? 0) > 1),
  }
}
