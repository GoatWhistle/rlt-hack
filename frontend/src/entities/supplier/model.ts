import type { CompanyRole, Contacts, RoleContext, Source } from "@/entities/evidence/model"

export const IDENTITY_STATUSES = ["verified", "unverified", "conflict"] as const
export type IdentityStatus = (typeof IDENTITY_STATUSES)[number]

export const AVAILABILITIES = ["available", "on_order", "unavailable", "unknown"] as const
export type Availability = (typeof AVAILABILITIES)[number]

export type Offer = {
  readonly id: string
  readonly name: string
  readonly price?: number
  readonly currency: string
  readonly unit: string
  readonly availability: Availability
  readonly source?: Source
}

export type SupplierProfile = {
  readonly id: string
  readonly name: string
  readonly inn: string
  readonly kpps: readonly string[]
  readonly region: string
  readonly identity: IdentityStatus
  readonly role: CompanyRole
  readonly roleSource?: Source
  readonly roleContext: RoleContext
  readonly contacts: Contacts
  readonly offers: readonly Offer[]
}
