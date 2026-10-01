export const PRODUCT_ORIGINS = ["notice", "inferred", "user"] as const
export type ProductOrigin = (typeof PRODUCT_ORIGINS)[number]

export const COMPANY_STATUSES = ["recommended", "check"] as const
export type CompanyStatus = (typeof COMPANY_STATUSES)[number]

export type Product = {
  readonly id: string
  readonly name: string
  readonly okpd2: string
  readonly origin: ProductOrigin
}

export type Evidence = {
  readonly kind: string
  readonly title: string
  readonly url: string
  readonly meta: string
}

export type Company = {
  readonly id: string
  readonly name: string
  readonly inn: string
  readonly role: string
  readonly status: CompanyStatus
  readonly coveredProductIds: readonly string[]
  readonly similarPurchases: number
  readonly why: readonly string[]
  readonly evidence: readonly Evidence[]
  readonly clarify: readonly string[]
}

export type Recommendation = {
  readonly fileName: string
  readonly requestTitle: string
  readonly lotLabel: string
  readonly products: readonly Product[]
  readonly companies: readonly Company[]
}
