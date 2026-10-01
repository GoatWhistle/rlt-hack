import {
  CANDIDATE_STATUSES,
  type CandidateStatus,
  type CheckReason,
  type CompanyRole,
  type Contacts,
  type Highlight,
  type MatchBasis,
  type PurchaseOutcome,
  type Source,
} from "@/entities/evidence/model"

export {
  CHECK_REASONS,
  type CheckReason,
  COMPANY_ROLES,
  type CompanyRole,
  type Contacts,
  HIGHLIGHT_CODES,
  type Highlight,
  type HighlightCode,
  MATCH_BASES,
  type MatchBasis,
  PURCHASE_OUTCOMES,
  type PurchaseOutcome,
  SOURCE_KINDS,
  type Source,
  type SourceKind,
} from "@/entities/evidence/model"

export const COMPANY_STATUSES = CANDIDATE_STATUSES
export type CompanyStatus = CandidateStatus

export const PRODUCT_ORIGINS = ["notice", "inferred", "user"] as const
export type ProductOrigin = (typeof PRODUCT_ORIGINS)[number]

export const ORIGIN_NOTE_CODES = ["similarPurchases", "userSpecified"] as const
export type OriginNoteCode = (typeof ORIGIN_NOTE_CODES)[number]

export type OriginNote =
  | { readonly code: "similarPurchases"; readonly hits: number; readonly total: number }
  | { readonly code: "userSpecified" }

export type Product = {
  readonly id: string
  readonly name: string
  readonly okpd2: string
  readonly origin: ProductOrigin
  readonly originNote?: OriginNote
}

export type ProductMatch = {
  readonly productId: string
  readonly basis: MatchBasis
  readonly source?: Source
}

export type Purchase = {
  readonly lotId?: string
  readonly title: string
  readonly year?: number
  readonly outcome: PurchaseOutcome
  readonly source?: Source
}

export type Company = {
  readonly id: string
  readonly name: string
  readonly inn: string
  readonly role: CompanyRole
  readonly roleSource?: Source
  readonly contacts?: Contacts
  readonly status: CompanyStatus
  readonly checkReasons: readonly CheckReason[]
  readonly highlights: readonly Highlight[]
  readonly matches: readonly ProductMatch[]
  readonly similarPurchases: number
  readonly wins: number
  readonly purchases: readonly Purchase[]
}

export type Recommendation = {
  readonly fileName: string
  readonly requestTitle: string
  readonly lotLabel: string
  readonly products: readonly Product[]
  readonly companies: readonly Company[]
}
