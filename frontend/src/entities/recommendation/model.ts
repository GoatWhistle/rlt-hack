export const PRODUCT_ORIGINS = ["notice", "inferred", "user"] as const
export type ProductOrigin = (typeof PRODUCT_ORIGINS)[number]

export const COMPANY_STATUSES = ["recommended", "check", "historical"] as const
export type CompanyStatus = (typeof COMPANY_STATUSES)[number]

export const MATCH_BASES = ["stock", "catalog", "inferred"] as const
export type MatchBasis = (typeof MATCH_BASES)[number]

export const SOURCE_KINDS = ["catalog", "price", "purchase", "registry"] as const
export type SourceKind = (typeof SOURCE_KINDS)[number]

export const COMPANY_ROLES = [
  "manufacturer",
  "distributor",
  "supplier",
  "supplierDistributor",
  "unknown",
] as const
export type CompanyRole = (typeof COMPANY_ROLES)[number]

export const CHECK_REASONS = ["roleUnconfirmed", "rangeUnconfirmed"] as const
export type CheckReason = (typeof CHECK_REASONS)[number]

export const ORIGIN_NOTE_CODES = ["similarPurchases", "userSpecified"] as const
export type OriginNoteCode = (typeof ORIGIN_NOTE_CODES)[number]

export type OriginNote =
  | { readonly code: "similarPurchases"; readonly hits: number; readonly total: number }
  | { readonly code: "userSpecified" }

export const PURCHASE_OUTCOMES = ["winner", "participant"] as const
export type PurchaseOutcome = (typeof PURCHASE_OUTCOMES)[number]

export type Source = {
  readonly kind: SourceKind
  readonly title: string
  readonly url: string
  readonly checkedAt?: string
}

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
  readonly year: number
  readonly outcome: PurchaseOutcome
  readonly source?: Source
}

export type Contacts = {
  readonly site?: string
  readonly email?: string
  readonly phone?: string
}

export type History = {
  readonly category: string
  readonly examples: readonly string[]
  readonly lastDate: string
}

export type CatalogOffer = {
  readonly name: string
  readonly url: string
  readonly checkedAt: string
}

export type Company = {
  readonly id: string
  readonly name: string
  readonly inn: string
  readonly role: CompanyRole
  readonly roleSource?: Source
  readonly contacts?: Contacts
  readonly status: CompanyStatus
  readonly checkReason?: CheckReason
  readonly summary: string
  readonly matches: readonly ProductMatch[]
  readonly similarPurchases: number | null
  readonly wins: number | null
  readonly purchases: readonly Purchase[]
  readonly clarify: readonly string[]
}

export type Recommendation = {
  readonly fileName: string
  readonly requestTitle: string
  readonly lotLabel: string
  readonly products: readonly Product[]
  readonly companies: readonly Company[]
}
