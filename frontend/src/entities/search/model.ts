import type {
  CandidateStatus,
  CheckReason,
  CompanyRole,
  Contacts,
  Highlight,
  MatchBasis,
  PurchaseOutcome,
  SearchWarning,
  Source,
} from "@/entities/evidence/model"
import type { Locale } from "@/shared/i18n/locale"

export {
  CANDIDATE_STATUSES,
  type CandidateStatus,
  CHECK_REASONS,
  type CheckReason,
  COMPANY_ROLES,
  type CompanyRole,
  HIGHLIGHT_CODES,
  type Highlight,
  type HighlightCode,
  MATCH_BASES,
  type MatchBasis,
  PURCHASE_OUTCOMES,
  type PurchaseOutcome,
  type SearchWarning,
  SOURCE_KINDS,
  type SourceKind,
  WARNING_CODES,
  type WarningCode,
} from "@/entities/evidence/model"

export const MAX_QUERY_LENGTH = 4000
export const DEFAULT_LIMIT = 20
export const RECENT_LIMIT = 8

export const ITEM_ORIGINS = ["text", "inferred", "user"] as const
export type ItemOrigin = (typeof ITEM_ORIGINS)[number]

export const ITEM_TYPES = ["unknown", "goods", "work", "service"] as const
export type ItemType = (typeof ITEM_TYPES)[number]

export const FILTER_ITEM_TYPES = ["goods", "work", "service"] as const
export type FilterItemType = (typeof FILTER_ITEM_TYPES)[number]

export type SearchFilters = {
  readonly regions?: readonly string[]
  readonly itemType?: FilterItemType
}

export type SearchRequest = {
  readonly text: string
  readonly limit?: number
  readonly filters?: SearchFilters
}

export type Quantity = {
  readonly value: string
  readonly unit: string
}

export type QueryItem = {
  readonly id: string
  readonly name: string
  readonly okpd2: string
  readonly itemType: ItemType
  readonly origin: ItemOrigin
  readonly quantity?: Quantity
}

export type CandidateMatch = {
  readonly itemId: string
  readonly basis: MatchBasis
  readonly offerId?: string
  readonly source?: Source
}

export type PurchaseRecord = {
  readonly lotId: string
  readonly title: string
  readonly outcome: PurchaseOutcome
  readonly itemIds: readonly string[]
}

export type PurchaseHistory = {
  readonly similarPurchases: number
  readonly wins: number
  readonly records: readonly PurchaseRecord[]
}

export type ChannelRank = {
  readonly channel: string
  readonly rank: number
}

export type Score = {
  readonly total: number
  readonly fusion: number
  readonly coverage: number
  readonly evidence: number
  readonly history: number
  readonly channels: readonly ChannelRank[]
}

export type Candidate = {
  readonly rank: number
  readonly id: string
  readonly name: string
  readonly inn: string
  readonly region: string
  readonly role: CompanyRole
  readonly roleSource?: Source
  readonly status: CandidateStatus
  readonly checkReasons: readonly CheckReason[]
  readonly matches: readonly CandidateMatch[]
  readonly history: PurchaseHistory
  readonly highlights: readonly Highlight[]
  readonly score: Score
  readonly contacts: Contacts
}

export type Pipeline = {
  readonly version: string
  readonly channels: readonly string[]
  readonly asOf: string
}

export type SearchQuery = {
  readonly text: string
  readonly locale: Locale
  readonly limit: number
  readonly filters: SearchFilters
}

export type SearchResult = {
  readonly searchId: string
  readonly query: SearchQuery
  readonly items: readonly QueryItem[]
  readonly candidates: readonly Candidate[]
  readonly pipeline: Pipeline
  readonly warnings: readonly SearchWarning[]
  readonly createdAt: string
}

export type SearchSummary = {
  readonly searchId: string
  readonly text: string
  readonly locale: Locale
  readonly items: number
  readonly candidates: number
  readonly recommended: number
  readonly createdAt: string
}

export function matchOf(candidate: Candidate, itemId: string): CandidateMatch | undefined {
  return candidate.matches.find((match) => match.itemId === itemId)
}

export function summaryOf(result: SearchResult): SearchSummary {
  return {
    searchId: result.searchId,
    text: result.query.text,
    locale: result.query.locale,
    items: result.items.length,
    candidates: result.candidates.length,
    recommended: result.candidates.filter((item) => item.status === "recommended").length,
    createdAt: result.createdAt,
  }
}
