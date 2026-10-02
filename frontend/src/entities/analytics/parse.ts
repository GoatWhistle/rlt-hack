import {
  count,
  type Fields,
  list,
  oneOf,
  optionalText,
  PayloadFormatError,
  plainText,
  record,
  text,
  withOptional,
} from "@/shared/api/payload"
import {
  ATTENTION_CODES,
  type Attention,
  type Category,
  type Count,
  FETCH_STATUSES,
  type Problem,
  type Ratio,
  type Run,
  type SnapshotMeta,
  SOURCE_STATES,
  SOURCE_TYPES,
  type SourceSummary,
} from "./model"

export function parseRatio(value: unknown, path: string): Ratio {
  const fields = record(value, path)
  const share = fields.share
  if (share !== null && (typeof share !== "number" || !Number.isFinite(share))) {
    throw new PayloadFormatError(`${path}.share`)
  }
  return {
    numerator: count(fields, "numerator", path),
    denominator: count(fields, "denominator", path),
    unknown: count(fields, "unknown", path),
    share,
  }
}

export function ratioOf(fields: Fields, key: string, path: string): Ratio {
  return parseRatio(fields[key], `${path}.${key}`)
}

export function parseCount(value: unknown, path: string): Count {
  const fields = record(value, path)
  return { key: text(fields, "key", path), count: count(fields, "count", path) }
}

export function parseMeta(value: unknown, path: string): SnapshotMeta {
  const fields = record(value, path)
  const policy = record(fields.policy, `${path}.policy`)
  return {
    snapshotId: text(fields, "snapshotId", path),
    asOf: text(fields, "asOf", path),
    computedAt: text(fields, "computedAt", path),
    definitionsVersion: text(fields, "definitionsVersion", path),
    delaySeconds: count(fields, "delaySeconds", path),
    warnings: list(fields, "warnings", path, plainText),
    policy: {
      offerDays: count(policy, "offerDays", `${path}.policy`),
      registryDays: count(policy, "registryDays", `${path}.policy`),
      periodDays: count(policy, "periodDays", `${path}.policy`),
    },
  }
}

export function parseAttention(value: unknown, path: string): Attention {
  const fields = record(value, path)
  return withOptional(
    {
      code: oneOf(ATTENTION_CODES, fields, "code", path),
      count: count(fields, "count", path),
      total: count(fields, "total", path),
    },
    { sourceId: optionalText(fields, "sourceId", path) },
  )
}

export function parseCategory(value: unknown, path: string): Category {
  const fields = record(value, path)
  return {
    code: text(fields, "code", path),
    name: text(fields, "name", path),
    parent: text(fields, "parent", path),
    offers: count(fields, "offers", path),
    share: ratioOf(fields, "share", path),
    companies: count(fields, "companies", path),
    verifiedSellers: ratioOf(fields, "verifiedSellers", path),
    fresh: ratioOf(fields, "fresh", path),
    priced: ratioOf(fields, "priced", path),
    searchable: ratioOf(fields, "searchable", path),
    systemAssigned: count(fields, "systemAssigned", path),
    sourceReported: count(fields, "sourceReported", path),
  }
}

export function parseSource(value: unknown, path: string): SourceSummary {
  const fields = record(value, path)
  return withOptional(
    {
      sourceId: text(fields, "sourceId", path),
      name: text(fields, "name", path),
      providerName: text(fields, "providerName", path),
      sourceType: oneOf(SOURCE_TYPES, fields, "sourceType", path),
      state: oneOf(SOURCE_STATES, fields, "state", path),
      offers: count(fields, "offers", path),
      companies: count(fields, "companies", path),
      fresh: ratioOf(fields, "fresh", path),
      runs: count(fields, "runs", path),
      failedRuns: count(fields, "failedRuns", path),
    },
    {
      lastSuccessAt: optionalText(fields, "lastSuccessAt", path),
      lastAttemptAt: optionalText(fields, "lastAttemptAt", path),
    },
  )
}

export function parseRun(value: unknown, path: string): Run {
  const fields = record(value, path)
  return {
    runId: text(fields, "runId", path),
    sourceId: text(fields, "sourceId", path),
    sourceName: text(fields, "sourceName", path),
    startedAt: text(fields, "startedAt", path),
    finishedAt: text(fields, "finishedAt", path),
    durationSeconds: count(fields, "durationSeconds", path),
    status: oneOf(FETCH_STATUSES, fields, "status", path),
    suppliersExtracted: count(fields, "suppliersExtracted", path),
    offersExtracted: count(fields, "offersExtracted", path),
    errorMessage: text(fields, "errorMessage", path),
  }
}

export function parseProblem(value: unknown, path: string): Problem {
  const fields = record(value, path)
  return {
    sourceId: text(fields, "sourceId", path),
    name: text(fields, "name", path),
    offers: count(fields, "offers", path),
    noSupplier: count(fields, "noSupplier", path),
    unverifiedSeller: count(fields, "unverifiedSeller", path),
    noCategory: count(fields, "noCategory", path),
    noPrice: count(fields, "noPrice", path),
    noAttributes: count(fields, "noAttributes", path),
    stale: count(fields, "stale", path),
    unknownAge: count(fields, "unknownAge", path),
  }
}
