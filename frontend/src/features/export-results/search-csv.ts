import type { SearchResult } from "@/entities/search/model"
import { slugOf } from "@/shared/download/slug"
import { CODE_SEPARATOR, type CsvLabels, NOTE_SEPARATOR, SUMMARY_SEPARATOR, toCsv } from "./csv"

export const SEARCH_COLUMNS = [
  "search_id",
  "rank",
  "supplier_inn",
  "supplier_name",
  "role",
  "region",
  "status",
  "check_reasons",
  "check_notes",
  "matched_items",
  "items_total",
  "stock_confirmed",
  "in_catalog",
  "assumed",
  "similar_purchases",
  "wins",
  "relevance",
  "summary",
  "site",
  "email",
  "phone",
] as const

export function searchCsv(
  result: SearchResult,
  labels: CsvLabels,
  chosen?: readonly string[],
): string {
  const keep = chosen ? new Set(chosen) : undefined
  const total = result.items.length
  const rows = result.candidates
    .filter((candidate) => !keep || keep.has(candidate.id))
    .map((candidate) => {
      const basis = (kind: string) => candidate.matches.filter((m) => m.basis === kind).length
      return [
        result.searchId,
        candidate.rank,
        candidate.inn,
        candidate.name,
        candidate.role,
        candidate.region,
        candidate.status,
        candidate.checkReasons.join(CODE_SEPARATOR),
        candidate.checkReasons.map(labels.checkReason).join(NOTE_SEPARATOR),
        candidate.matches.length,
        total,
        basis("stock"),
        basis("catalog"),
        basis("inferred"),
        candidate.history.similarPurchases,
        candidate.history.wins,
        candidate.score.total,
        candidate.highlights.map(labels.highlight).join(SUMMARY_SEPARATOR),
        candidate.contacts.site ?? "",
        candidate.contacts.email ?? "",
        candidate.contacts.phone ?? "",
      ]
    })
  return toCsv(SEARCH_COLUMNS, rows)
}

export const FILE_PREFIX = "lotive"

export function searchFileName(text: string, createdAt: string): string {
  const day = createdAt.slice(0, 10)
  return `${[FILE_PREFIX, slugOf(text) || "search", day].filter(Boolean).join("-")}.csv`
}
