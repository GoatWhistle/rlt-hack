import {
  parseCheckReasons,
  parseContacts,
  parseHighlights,
  parseSource,
  parseWarnings,
} from "@/entities/evidence/parse"
import {
  count,
  type Fields,
  list,
  oneOf,
  optionalOneOf,
  optionalText,
  PayloadFormatError,
  plainText,
  record,
  text,
  withOptional,
} from "@/shared/api/payload"
import { LOCALES } from "@/shared/i18n/locale"
import {
  CANDIDATE_STATUSES,
  type Candidate,
  type CandidateMatch,
  COMPANY_ROLES,
  ITEM_ORIGINS,
  ITEM_TYPES,
  MATCH_BASES,
  PURCHASE_OUTCOMES,
  type PurchaseHistory,
  type PurchaseRecord,
  type QueryItem,
  type Score,
  type SearchFilters,
  type SearchQuery,
  type SearchResult,
  type SearchSummary,
} from "./model"

function fraction(fields: Fields, key: string, path: string): number {
  const value = fields[key]
  if (typeof value !== "number" || !Number.isFinite(value) || value < 0 || value > 1) {
    throw new PayloadFormatError(`${path}.${key}`)
  }
  return value
}

function nested(fields: Fields, key: string, path: string): Fields {
  return record(fields[key], `${path}.${key}`)
}

function filters(value: unknown, path: string): SearchFilters {
  if (value === undefined || value === null) return {}
  const fields = record(value, path)
  return withOptional(
    {},
    {
      regions:
        fields.regions === undefined || fields.regions === null
          ? undefined
          : list(fields, "regions", path, plainText),
      itemType: optionalOneOf(ITEM_TYPES, fields, "itemType", path),
    },
  )
}

function query(value: unknown, path: string): SearchQuery {
  const fields = record(value, path)
  return {
    text: text(fields, "text", path),
    locale: oneOf(LOCALES, fields, "locale", path),
    limit: count(fields, "limit", path),
    filters: filters(fields.filters, `${path}.filters`),
  }
}

function item(value: unknown, path: string): QueryItem {
  const fields = record(value, path)
  const quantity =
    fields.quantity === undefined || fields.quantity === null
      ? undefined
      : nested(fields, "quantity", path)
  return withOptional(
    {
      id: text(fields, "id", path),
      name: text(fields, "name", path),
      okpd2: text(fields, "okpd2", path),
      itemType: oneOf(ITEM_TYPES, fields, "itemType", path),
      origin: oneOf(ITEM_ORIGINS, fields, "origin", path),
    },
    {
      quantity: quantity && {
        value: text(quantity, "value", `${path}.quantity`),
        unit: text(quantity, "unit", `${path}.quantity`),
      },
    },
  )
}

function match(value: unknown, path: string): CandidateMatch {
  const fields = record(value, path)
  return withOptional(
    { itemId: text(fields, "itemId", path), basis: oneOf(MATCH_BASES, fields, "basis", path) },
    {
      offerId: optionalText(fields, "offerId", path),
      source: parseSource(fields.source, `${path}.source`),
    },
  )
}

function purchase(value: unknown, path: string): PurchaseRecord {
  const fields = record(value, path)
  return {
    lotId: text(fields, "lotId", path),
    title: text(fields, "title", path),
    outcome: oneOf(PURCHASE_OUTCOMES, fields, "outcome", path),
    itemIds: list(fields, "itemIds", path, plainText),
  }
}

function history(fields: Fields, path: string): PurchaseHistory {
  return {
    similarPurchases: count(fields, "similarPurchases", path),
    wins: count(fields, "wins", path),
    records: list(fields, "records", path, purchase),
  }
}

function score(fields: Fields, path: string): Score {
  return {
    total: fraction(fields, "total", path),
    fusion: fraction(fields, "fusion", path),
    coverage: fraction(fields, "coverage", path),
    evidence: fraction(fields, "evidence", path),
    history: fraction(fields, "history", path),
    channels: list(fields, "channels", path, (entry, at) => {
      const channel = record(entry, at)
      return { channel: text(channel, "channel", at), rank: count(channel, "rank", at) }
    }),
  }
}

function candidate(value: unknown, path: string): Candidate {
  const fields = record(value, path)
  return withOptional(
    {
      rank: count(fields, "rank", path),
      id: text(fields, "id", path),
      name: text(fields, "name", path),
      inn: text(fields, "inn", path),
      region: text(fields, "region", path),
      role: oneOf(COMPANY_ROLES, fields, "role", path),
      status: oneOf(CANDIDATE_STATUSES, fields, "status", path),
      checkReasons: parseCheckReasons(fields, path),
      matches: list(fields, "matches", path, match),
      history: history(nested(fields, "history", path), `${path}.history`),
      highlights: parseHighlights(fields, path),
      score: score(nested(fields, "score", path), `${path}.score`),
      contacts: parseContacts(nested(fields, "contacts", path), `${path}.contacts`) ?? {},
    },
    { roleSource: parseSource(fields.roleSource, `${path}.roleSource`) },
  )
}

function checkLinks(result: SearchResult): SearchResult {
  const known = new Set(result.items.map((entry) => entry.id))
  result.candidates.forEach((entry, index) => {
    const broken = entry.matches.findIndex((found) => !known.has(found.itemId))
    if (broken >= 0) throw new PayloadFormatError(`$.candidates[${index}].matches[${broken}]`)
  })
  return result
}

export function parseSearchResult(value: unknown): SearchResult {
  const fields = record(value, "$")
  const pipeline = nested(fields, "pipeline", "$")
  return checkLinks({
    searchId: text(fields, "searchId", "$"),
    query: query(fields.query, "$.query"),
    items: list(fields, "items", "$", item),
    candidates: list(fields, "candidates", "$", candidate),
    pipeline: {
      version: text(pipeline, "version", "$.pipeline"),
      channels: list(pipeline, "channels", "$.pipeline", plainText),
      asOf: text(pipeline, "asOf", "$.pipeline"),
    },
    warnings: parseWarnings(fields, "$"),
    createdAt: text(fields, "createdAt", "$"),
  })
}

function summary(value: unknown, path: string): SearchSummary {
  const fields = record(value, path)
  return {
    searchId: text(fields, "searchId", path),
    text: text(fields, "text", path),
    locale: oneOf(LOCALES, fields, "locale", path),
    items: count(fields, "items", path),
    candidates: count(fields, "candidates", path),
    recommended: count(fields, "recommended", path),
    createdAt: text(fields, "createdAt", path),
  }
}

export function parseRecentSearches(value: unknown): SearchSummary[] {
  return list(record(value, "$"), "searches", "$", summary)
}
