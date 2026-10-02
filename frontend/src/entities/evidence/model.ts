export const SOURCE_KINDS = ["catalog", "price", "purchase", "registry"] as const
export type SourceKind = (typeof SOURCE_KINDS)[number]

export const MATCH_BASES = ["stock", "catalog", "inferred"] as const
export type MatchBasis = (typeof MATCH_BASES)[number]
export type MeterBasis = MatchBasis | "none"

export const CANDIDATE_STATUSES = ["recommended", "check"] as const
export type CandidateStatus = (typeof CANDIDATE_STATUSES)[number]

export const COMPANY_ROLES = [
  "manufacturer",
  "distributor",
  "supplier",
  "supplierDistributor",
  "serviceProvider",
  "unknown",
] as const
export type CompanyRole = (typeof COMPANY_ROLES)[number]

export const PURCHASE_OUTCOMES = ["winner", "participant"] as const
export type PurchaseOutcome = (typeof PURCHASE_OUTCOMES)[number]

export type Source = {
  readonly kind: SourceKind
  readonly title: string
  readonly url: string
  readonly checkedAt?: string
}

export const AVAILABILITIES = ["available", "on_order", "unavailable", "unknown"] as const
export type Availability = (typeof AVAILABILITIES)[number]

export const SELLER_STATUSES = ["verified", "unverified", "conflict"] as const
export type SellerStatus = (typeof SELLER_STATUSES)[number]

export const STALE_AFTER_DAYS = 30
const DAY_MS = 86_400_000

export type OfferAttribute = {
  readonly name: string
  readonly value: string
}

export type OfferView = {
  readonly id: string
  readonly name: string
  readonly price?: number
  readonly currency?: string
  readonly unit?: string
  readonly availability?: Availability
  readonly brand?: string
  readonly article?: string
  readonly okpd2?: string
  readonly attributes?: readonly OfferAttribute[]
  readonly imageUrl?: string
  readonly seller?: SellerStatus
  readonly source?: Source
}

export function isStale(checkedAt: string | undefined, now: number = Date.now()): boolean {
  if (!checkedAt) return false
  const moment = Date.parse(checkedAt)
  return Number.isFinite(moment) && now - moment > STALE_AFTER_DAYS * DAY_MS
}

export type Contacts = {
  readonly site?: string
  readonly email?: string
  readonly phone?: string
}

export function hasContacts(contacts: Contacts | undefined): boolean {
  return Boolean(contacts?.site || contacts?.email || contacts?.phone)
}

export const CHECK_REASONS = [
  "innMissing",
  "identityConflict",
  "roleUnconfirmed",
  "noCurrentOffer",
  "rangeUnconfirmed",
  "sourceUnavailable",
] as const
export type CheckReason = (typeof CHECK_REASONS)[number]

export const HIGHLIGHT_CODES = [
  "coversItems",
  "inStock",
  "hasPrice",
  "pastWins",
  "similarPurchases",
  "verifiedIdentity",
] as const
export type HighlightCode = (typeof HIGHLIGHT_CODES)[number]

export type Highlight = {
  readonly code: HighlightCode
  readonly params: Readonly<Record<string, number>>
}

export const WARNING_CODES = [
  "channelFailed",
  "enrichmentFailed",
  "archiveFailed",
  "itemsInferred",
  "itemsTruncated",
] as const
export type WarningCode = (typeof WARNING_CODES)[number]

export const DEGRADING_WARNINGS: readonly WarningCode[] = ["channelFailed", "enrichmentFailed"]

export type SearchWarning = {
  readonly code: WarningCode
  readonly subject: string
}

export type MatchCount = {
  readonly confirmed: number
  readonly assumed: number
}

export function countMatches(matches: readonly { readonly basis: MatchBasis }[]): MatchCount {
  const assumed = matches.filter((match) => match.basis === "inferred").length
  return { confirmed: matches.length - assumed, assumed }
}
