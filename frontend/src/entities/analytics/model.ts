export const SOURCE_TYPES = [
  "directory",
  "website",
  "feed",
  "price_list",
  "registry",
  "dataset",
] as const
export type SourceType = (typeof SOURCE_TYPES)[number]

export const FETCH_STATUSES = ["success", "partial", "failed"] as const
export type FetchStatus = (typeof FETCH_STATUSES)[number]

export const SOURCE_STATES = ["ok", "partial", "failed", "never_run"] as const
export type SourceState = (typeof SOURCE_STATES)[number]

export const ATTENTION_CODES = [
  "source_never_run",
  "source_failed",
  "source_stale",
  "no_category",
  "no_verified_seller",
] as const
export type AttentionCode = (typeof ATTENTION_CODES)[number]

export const RECORD_PROBLEMS = [
  "stale",
  "unknown_age",
  "no_category",
  "no_price",
  "no_supplier",
  "unverified_seller",
  "no_attributes",
] as const
export type RecordProblem = (typeof RECORD_PROBLEMS)[number]

export type Ratio = {
  readonly numerator: number
  readonly denominator: number
  readonly unknown: number
  readonly share: number | null
}

export type Count = { readonly key: string; readonly count: number }

export type AnalyticsFilters = {
  readonly sourceId?: string
  readonly sourceType?: SourceType
  readonly region?: string
}

export type SnapshotMeta = {
  readonly snapshotId: string
  readonly asOf: string
  readonly computedAt: string
  readonly definitionsVersion: string
  readonly delaySeconds: number
  readonly warnings: readonly string[]
  readonly policy: {
    readonly offerDays: number
    readonly registryDays: number
    readonly periodDays: number
  }
}

export type Attention = {
  readonly code: AttentionCode
  readonly sourceId?: string
  readonly count: number
  readonly total: number
}

export type Category = {
  readonly code: string
  readonly name: string
  readonly parent: string
  readonly offers: number
  readonly share: Ratio
  readonly companies: number
  readonly verifiedSellers: Ratio
  readonly fresh: Ratio
  readonly priced: Ratio
  readonly searchable: Ratio
  readonly systemAssigned: number
  readonly sourceReported: number
}

export type SourceSummary = {
  readonly sourceId: string
  readonly name: string
  readonly providerName: string
  readonly sourceType: SourceType
  readonly state: SourceState
  readonly offers: number
  readonly companies: number
  readonly fresh: Ratio
  readonly lastSuccessAt?: string
  readonly lastAttemptAt?: string
  readonly runs: number
  readonly failedRuns: number
}

export type Run = {
  readonly runId: string
  readonly sourceId: string
  readonly sourceName: string
  readonly startedAt: string
  readonly finishedAt: string
  readonly durationSeconds: number
  readonly status: FetchStatus
  readonly suppliersExtracted: number
  readonly offersExtracted: number
  readonly errorMessage: string
}

export type Problem = {
  readonly sourceId: string
  readonly name: string
  readonly offers: number
  readonly noSupplier: number
  readonly unverifiedSeller: number
  readonly noCategory: number
  readonly noPrice: number
  readonly noAttributes: number
  readonly stale: number
  readonly unknownAge: number
}

export type Overview = {
  readonly meta: SnapshotMeta
  readonly offers: number
  readonly companies: number
  readonly composition: readonly Count[]
  readonly fresh: Ratio
  readonly searchable: Ratio
  readonly runsSuccess: Ratio
  readonly runsPartial: number
  readonly attention: readonly Attention[]
  readonly categories: readonly Category[]
  readonly sources: readonly SourceSummary[]
  readonly runs: readonly Run[]
}

export type CategoriesReport = {
  readonly meta: SnapshotMeta
  readonly offers: number
  readonly items: readonly Category[]
  readonly origins: readonly Count[]
}

export type QualityReport = {
  readonly meta: SnapshotMeta
  readonly offers: number
  readonly fresh: Ratio
  readonly priced: Ratio
  readonly age: readonly Count[]
  readonly availability: readonly Count[]
  readonly problems: readonly Problem[]
}

export type SourcesReport = {
  readonly meta: SnapshotMeta
  readonly items: readonly SourceSummary[]
  readonly runs: readonly Run[]
  readonly success: Ratio
  readonly partial: number
}

export type RecordItem = {
  readonly offerId: string
  readonly name: string
  readonly sourceName: string
  readonly supplierName: string
  readonly okpd2Code: string
  readonly price?: number
  readonly currency: string
  readonly url: string
  readonly lastSeenAt: string
}

export type RecordsQuery = {
  readonly category?: string
  readonly problem?: RecordProblem
  readonly offset: number
  readonly limit: number
}

export type RecordsPage = {
  readonly asOf: string
  readonly total: number
  readonly changedAfter: number
  readonly items: readonly RecordItem[]
}
