import { count, list, optionalAmount, record, text } from "@/shared/api/payload"
import type {
  CategoriesReport,
  Overview,
  QualityReport,
  RecordItem,
  RecordsPage,
} from "./model"
import {
  parseAttention,
  parseCategory,
  parseCount,
  parseMeta,
  parseProblem,
  parseRatio,
  parseRun,
  parseSource,
  ratioOf,
} from "./parse"

export function parseOverview(value: unknown): Overview {
  const fields = record(value, "$")
  return {
    meta: parseMeta(fields.meta, "$.meta"),
    offers: count(fields, "offers", "$"),
    companies: count(fields, "companies", "$"),
    composition: list(fields, "composition", "$", parseCount),
    fresh: ratioOf(fields, "fresh", "$"),
    searchable: ratioOf(fields, "searchable", "$"),
    runsSuccess: ratioOf(fields, "runsSuccess", "$"),
    runsPartial: count(fields, "runsPartial", "$"),
    attention: list(fields, "attention", "$", parseAttention),
    categories: list(fields, "categories", "$", parseCategory),
    sources: list(fields, "sources", "$", parseSource),
    runs: list(fields, "runs", "$", parseRun),
  }
}

export function parseCategories(value: unknown): CategoriesReport {
  const fields = record(value, "$")
  return {
    meta: parseMeta(fields.meta, "$.meta"),
    offers: count(fields, "offers", "$"),
    items: list(fields, "items", "$", parseCategory),
    origins: list(fields, "origins", "$", parseCount),
  }
}

export function parseQuality(value: unknown): QualityReport {
  const fields = record(value, "$")
  return {
    meta: parseMeta(fields.meta, "$.meta"),
    offers: count(fields, "offers", "$"),
    fresh: ratioOf(fields, "fresh", "$"),
    priced: ratioOf(fields, "priced", "$"),
    age: list(fields, "age", "$", parseCount),
    availability: list(fields, "availability", "$", parseCount),
    problems: list(fields, "problems", "$", parseProblem),
  }
}

export function parseSources(value: unknown) {
  const fields = record(value, "$")
  return {
    meta: parseMeta(fields.meta, "$.meta"),
    items: list(fields, "items", "$", parseSource),
  }
}

export function parseRuns(value: unknown) {
  const fields = record(value, "$")
  return {
    meta: parseMeta(fields.meta, "$.meta"),
    success: parseRatio(fields.success, "$.success"),
    partial: count(fields, "partial", "$"),
    items: list(fields, "items", "$", parseRun),
  }
}

function parseRecord(value: unknown, path: string): RecordItem {
  const fields = record(value, path)
  const price = optionalAmount(fields, "price", path)
  return {
    offerId: text(fields, "offerId", path),
    name: text(fields, "name", path),
    sourceName: text(fields, "sourceName", path),
    supplierName: text(fields, "supplierName", path),
    okpd2Code: text(fields, "okpd2Code", path),
    ...(price === undefined ? {} : { price }),
    currency: text(fields, "currency", path),
    url: text(fields, "url", path),
    lastSeenAt: text(fields, "lastSeenAt", path),
  }
}

export function parseRecords(value: unknown): RecordsPage {
  const fields = record(value, "$")
  return {
    asOf: text(fields, "asOf", "$"),
    total: count(fields, "total", "$"),
    changedAfter: count(fields, "changedAfter", "$"),
    items: list(fields, "items", "$", parseRecord),
  }
}
