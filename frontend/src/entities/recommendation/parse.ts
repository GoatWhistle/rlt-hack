import {
  COMPANY_STATUSES,
  type Company,
  type Evidence,
  PRODUCT_ORIGINS,
  type Product,
  type Recommendation,
} from "./model"

export class RecommendationFormatError extends Error {
  constructor(path: string) {
    super(`unexpected recommendation payload at ${path}`)
    this.name = "RecommendationFormatError"
  }
}

type Fields = Readonly<Record<string, unknown>>

function record(value: unknown, path: string): Fields {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw new RecommendationFormatError(path)
  }
  return value as Fields
}

function text(fields: Fields, key: string, path: string): string {
  const value = fields[key]
  if (typeof value !== "string") throw new RecommendationFormatError(`${path}.${key}`)
  return value
}

function count(fields: Fields, key: string, path: string): number {
  const value = fields[key]
  if (typeof value !== "number" || !Number.isFinite(value)) {
    throw new RecommendationFormatError(`${path}.${key}`)
  }
  return value
}

function list<T>(
  fields: Fields,
  key: string,
  path: string,
  item: (value: unknown, at: string) => T,
): T[] {
  const value = fields[key]
  if (!Array.isArray(value)) throw new RecommendationFormatError(`${path}.${key}`)
  return value.map((entry, index) => item(entry, `${path}.${key}[${index}]`))
}

function oneOf<T extends string>(options: readonly T[], value: string, path: string): T {
  const found = options.find((option) => option === value)
  if (!found) throw new RecommendationFormatError(path)
  return found
}

function plainText(value: unknown, path: string): string {
  if (typeof value !== "string") throw new RecommendationFormatError(path)
  return value
}

function product(value: unknown, path: string): Product {
  const fields = record(value, path)
  return {
    id: text(fields, "id", path),
    name: text(fields, "name", path),
    okpd2: text(fields, "okpd2", path),
    origin: oneOf(PRODUCT_ORIGINS, text(fields, "origin", path), `${path}.origin`),
  }
}

function evidence(value: unknown, path: string): Evidence {
  const fields = record(value, path)
  return {
    kind: text(fields, "kind", path),
    title: text(fields, "title", path),
    url: text(fields, "url", path),
    meta: text(fields, "meta", path),
  }
}

function company(value: unknown, path: string): Company {
  const fields = record(value, path)
  return {
    id: text(fields, "id", path),
    name: text(fields, "name", path),
    inn: text(fields, "inn", path),
    role: text(fields, "role", path),
    status: oneOf(COMPANY_STATUSES, text(fields, "status", path), `${path}.status`),
    coveredProductIds: list(fields, "coveredProductIds", path, plainText),
    similarPurchases: count(fields, "similarPurchases", path),
    why: list(fields, "why", path, plainText),
    evidence: list(fields, "evidence", path, evidence),
    clarify: list(fields, "clarify", path, plainText),
  }
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
