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

export const CANDIDATE_ORIGINS = ["catalog", "history"] as const
export type CandidateOrigin = (typeof CANDIDATE_ORIGINS)[number]

export const NOVELTIES = ["new", "known", "unknown"] as const
export type Novelty = (typeof NOVELTIES)[number]

export const PURCHASE_OUTCOMES = ["winner", "participant"] as const
export type PurchaseOutcome = (typeof PURCHASE_OUTCOMES)[number]

export type Source = {
  readonly kind: SourceKind
  readonly title: string
  readonly url: string
  readonly checkedAt?: string
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
