import {
  parseCheck,
  parseCheckReasons,
  parseContacts,
  parseHighlights,
  parseOffer,
  parseRequirement,
  parseRoleContext,
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
  CANDIDATE_ORIGINS,
  CANDIDATE_STATUSES,
  type Candidate,
  type CandidateMatch,
  type CandidateOrigin,
  COMPANY_ROLES,
  ITEM_ORIGINS,
  ITEM_TYPES,
  MATCH_BASES,
  NOVELTIES,
  PURCHASE_OUTCOMES,
  type PurchaseHistory,
  type PurchaseRecord,
  type QueryItem,
  type Score,
  type SearchResult,
  type SearchSummary,
} from "./model"
import { parseQuery } from "./query-parse"

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
      requirements:
        fields.requirements === undefined
          ? []
          : list(fields, "requirements", path, parseRequirement),
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
    {
      itemId: text(fields, "itemId", path),
      basis: oneOf(MATCH_BASES, fields, "basis", path),
      checks: fields.checks === undefined ? [] : list(fields, "checks", path, parseCheck),
    },
    {
      offerId: optionalText(fields, "offerId", path),
      source: parseSource(fields.source, `${path}.source`),
      offer: parseOffer(fields.offer, `${path}.offer`),
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
      origins: origins(fields, path),
      novelty: optionalOneOf(NOVELTIES, fields, "novelty", path) ?? "unknown",
      roleContext: parseRoleContext(fields, path),
    },
    { roleSource: parseSource(fields.roleSource, `${path}.roleSource`) },
  )
}

function origins(fields: Fields, path: string): CandidateOrigin[] {
  if (fields.origins === undefined) return []
  const known: readonly string[] = CANDIDATE_ORIGINS
  return list(fields, "origins", path, plainText).filter((code): code is CandidateOrigin =>
    known.includes(code),
  )
}

function checkLinks(result: SearchResult, path: string): SearchResult {
  const known = new Set(result.items.map((entry) => entry.id))
  result.candidates.forEach((entry, index) => {
    const broken = entry.matches.findIndex((found) => !known.has(found.itemId))
    if (broken >= 0) {
      throw new PayloadFormatError(`${path}.candidates[${index}].matches[${broken}]`)
    }
  })
  return result
}

export function parseSearchResult(value: unknown, path = "$"): SearchResult {
  const fields = record(value, path)
  const pipeline = nested(fields, "pipeline", path)
  const at = `${path}.pipeline`
  return checkLinks(
    {
      searchId: text(fields, "searchId", path),
      query: parseQuery(fields.query, `${path}.query`),
      items: list(fields, "items", path, item),
      candidates: list(fields, "candidates", path, candidate),
      pipeline: {
        version: text(pipeline, "version", at),
        channels: list(pipeline, "channels", at, plainText),
        asOf: text(pipeline, "asOf", at),
        inputs:
          pipeline.inputs === undefined ? ["text"] : list(pipeline, "inputs", at, plainText),
        ...withOptional({}, { noveltySet: optionalText(pipeline, "noveltySet", at) }),
      },
      warnings: parseWarnings(fields, path),
      createdAt: text(fields, "createdAt", path),
    },
    path,
  )
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
