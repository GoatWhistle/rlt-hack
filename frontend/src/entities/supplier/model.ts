import type { CompanyRole, Contacts, OfferView, Source } from "@/entities/evidence/model"

export { AVAILABILITIES, type Availability } from "@/entities/evidence/model"

export const IDENTITY_STATUSES = ["verified", "unverified", "conflict"] as const
export type IdentityStatus = (typeof IDENTITY_STATUSES)[number]

export type Offer = OfferView

export type SupplierProfile = {
  readonly id: string
  readonly name: string
  readonly inn: string
  readonly kpps: readonly string[]
  readonly region: string
  readonly identity: IdentityStatus
  readonly role: CompanyRole
  readonly roleSource?: Source
  readonly contacts: Contacts
  readonly offers: readonly Offer[]
}
