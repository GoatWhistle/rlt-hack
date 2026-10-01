import {
  parseCheckReasons,
  parseContacts,
  parseHighlights,
  parseSource,
} from "@/entities/evidence/parse"
import {
  count,
  type Fields,
  list,
  oneOf,
  optionalText,
  record,
  text,
  withOptional,
} from "@/shared/api/payload"
import {
  COMPANY_ROLES,
  COMPANY_STATUSES,
  type Company,
  MATCH_BASES,
  ORIGIN_NOTE_CODES,
  type OriginNote,
  PRODUCT_ORIGINS,
  type Product,
  type ProductMatch,
  PURCHASE_OUTCOMES,
  type Purchase,
  type Recommendation,
} from "./model"

export { PayloadFormatError } from "@/shared/api/payload"

function optionalCount(fields: Fields, key: string, path: string): number | undefined {
  const value = fields[key]
  return value === undefined || value === null ? undefined : count(fields, key, path)
}

function originNote(value: unknown, path: string): OriginNote | undefined {
  if (value === undefined || value === null) return undefined
  const fields = record(value, path)
  const code = oneOf(ORIGIN_NOTE_CODES, fields, "code", path)
  if (code === "userSpecified") return { code }
  return { code, hits: count(fields, "hits", path), total: count(fields, "total", path) }
}

function product(value: unknown, path: string): Product {
  const fields = record(value, path)
  return withOptional(
    {
      id: text(fields, "id", path),
      name: text(fields, "name", path),
      okpd2: text(fields, "okpd2", path),
      origin: oneOf(PRODUCT_ORIGINS, fields, "origin", path),
    },
    { originNote: originNote(fields.originNote, `${path}.originNote`) },
  )
}

function match(value: unknown, path: string): ProductMatch {
  const fields = record(value, path)
  return withOptional(
    {
      productId: text(fields, "productId", path),
      basis: oneOf(MATCH_BASES, fields, "basis", path),
    },
    { source: parseSource(fields.source, `${path}.source`) },
  )
}

function purchase(value: unknown, path: string): Purchase {
  const fields = record(value, path)
  return withOptional(
    {
      title: text(fields, "title", path),
      outcome: oneOf(PURCHASE_OUTCOMES, fields, "outcome", path),
    },
    {
      year: optionalCount(fields, "year", path),
      lotId: optionalText(fields, "lotId", path),
      source: parseSource(fields.source, `${path}.source`),
    },
  )
}

function history(value: unknown, path: string): History | undefined {
  if (value === undefined || value === null) return undefined
  const fields = record(value, path)
  return {
    category: text(fields, "category", path),
    examples: list(fields, "examples", path, plainText),
    lastDate: text(fields, "lastDate", path),
  }
}

function catalogOffer(value: unknown, path: string): CatalogOffer {
  const fields = record(value, path)
  return {
    name: text(fields, "name", path),
    url: text(fields, "url", path),
    checkedAt: text(fields, "checkedAt", path),
  }
}

function company(value: unknown, path: string): Company {
  const fields = record(value, path)
  return withOptional(
    {
      id: text(fields, "id", path),
      name: text(fields, "name", path),
      inn: text(fields, "inn", path),
      role: oneOf(COMPANY_ROLES, fields, "role", path),
      status: oneOf(COMPANY_STATUSES, fields, "status", path),
      checkReasons: parseCheckReasons(fields, path),
      highlights: parseHighlights(fields, path),
      matches: list(fields, "matches", path, match),
      similarPurchases: count(fields, "similarPurchases", path),
      wins: count(fields, "wins", path),
      purchases: list(fields, "purchases", path, purchase),
    },
    {
      roleSource: parseSource(fields.roleSource, `${path}.roleSource`),
      contacts: parseContacts(fields.contacts, `${path}.contacts`),
    },
  )
}

export function parseRecommendation(value: unknown): Recommendation {
  const fields = record(value, "$")
  return {
    fileName: text(fields, "fileName", "$"),
    requestTitle: text(fields, "requestTitle", "$"),
    lotLabel: text(fields, "lotLabel", "$"),
    products: list(fields, "products", "$", product),
    companies: list(fields, "companies", "$", company),
  }
}
