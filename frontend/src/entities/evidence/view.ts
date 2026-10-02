import type {
  CandidateStatus,
  CheckReason,
  CompanyRole,
  Contacts,
  Highlight,
  MatchBasis,
  MeterBasis,
  OfferView,
  PurchaseOutcome,
  Source,
} from "./model"

export type ItemView = {
  readonly id: string
  readonly name: string
}

export type MatchView = {
  readonly itemId: string
  readonly basis: MatchBasis
  readonly source?: Source
  readonly offerId?: string
  readonly offer?: OfferView
}

export type PurchaseView = {
  readonly key: string
  readonly lotId?: string
  readonly title: string
  readonly year?: number
  readonly url?: string
  readonly outcome: PurchaseOutcome
  readonly itemIds: readonly string[]
}

export type CandidateView = {
  readonly id: string
  readonly rank: number
  readonly name: string
  readonly inn: string
  readonly role: CompanyRole
  readonly roleSource?: Source
  readonly region?: string
  readonly contacts?: Contacts
  readonly status: CandidateStatus
  readonly checkReasons: readonly CheckReason[]
  readonly highlights: readonly Highlight[]
  readonly matches: readonly MatchView[]
  readonly similarPurchases: number
  readonly wins: number
  readonly purchases: readonly PurchaseView[]
}

export type RowView = {
  readonly item: ItemView
  readonly match?: MatchView
}

export const REASON_ORDER: readonly CheckReason[] = [
  "identityConflict",
  "innMissing",
  "roleUnconfirmed",
  "noCurrentOffer",
  "rangeUnconfirmed",
  "sourceUnavailable",
]

const BASIS_RANK: Record<MatchBasis, number> = { stock: 0, catalog: 1, inferred: 2 }

export function sortReasons(reasons: readonly CheckReason[]): CheckReason[] {
  return [...reasons].sort((a, b) => REASON_ORDER.indexOf(a) - REASON_ORDER.indexOf(b))
}

export function matchFor(candidate: CandidateView, itemId: string): MatchView | undefined {
  return candidate.matches.find((match) => match.itemId === itemId)
}

export function segmentsOf(
  candidate: CandidateView,
  items: readonly ItemView[],
): { readonly key: string; readonly basis: MeterBasis }[] {
  return items.map((item) => ({
    key: item.id,
    basis: matchFor(candidate, item.id)?.basis ?? "none",
  }))
}

export function rowsOf(candidate: CandidateView, items: readonly ItemView[]): RowView[] {
  const rank = (row: RowView) => (row.match ? BASIS_RANK[row.match.basis] : 3)
  return items
    .map((item) => ({ item, match: matchFor(candidate, item.id) }))
    .sort((a, b) => rank(a) - rank(b))
}

export type FreshSource = {
  readonly basis: "stock" | "catalog"
  readonly count: number
  readonly checkedAt?: string
}

export function freshestOf(candidate: CandidateView): FreshSource | undefined {
  for (const basis of ["stock", "catalog"] as const) {
    const found = candidate.matches.filter((match) => match.basis === basis)
    if (found.length === 0) continue
    const dates = found.flatMap((match) => match.source?.checkedAt ?? []).sort()
    return { basis, count: found.length, checkedAt: dates.at(-1) }
  }
  return undefined
}

export function lastWinOf(candidate: CandidateView): PurchaseView | undefined {
  return candidate.purchases.find((purchase) => purchase.outcome === "winner" && purchase.lotId)
}

export function coverageOf(candidate: CandidateView, itemId: string | null): boolean {
  return itemId === null || matchFor(candidate, itemId) !== undefined
}
