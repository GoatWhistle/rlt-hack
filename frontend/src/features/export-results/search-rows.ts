import { coverageOf } from "@/entities/search/coverage"
import type { Candidate, QueryItem, SearchResult } from "@/entities/search/model"
import {
  type Cell,
  CODE_SEPARATOR,
  type CsvLabels,
  NOTE_SEPARATOR,
  SUMMARY_SEPARATOR,
} from "./csv"

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
  "role_basis",
  "role_note",
  "novelty",
  "origins",
  "items_confirmed",
  "items_to_clarify",
  "evidence",
  "result_created_at",
] as const

const EVIDENCE_SEPARATOR = " | "

function evidenceOf(candidate: Candidate, items: readonly QueryItem[]): string {
  return items
    .flatMap((item) => {
      const match = candidate.matches.find((entry) => entry.itemId === item.id)
      const offer = match?.offer
      if (!offer) return []
      const checks = match.checks
        .map((check) => `${check.text}:${check.status}`)
        .join(CODE_SEPARATOR)
      return [
        [item.name, offer.name, offer.url, offer.observedAt.slice(0, 10), checks].join(
          NOTE_SEPARATOR,
        ),
      ]
    })
    .join(EVIDENCE_SEPARATOR)
}

export function candidateRows(
  result: SearchResult,
  labels: CsvLabels,
  chosen?: readonly string[],
): Cell[][] {
  const keep = chosen ? new Set(chosen) : undefined
  const total = result.items.length
  return result.candidates
    .filter((candidate) => !keep || keep.has(candidate.id))
    .map((candidate) => {
      const basis = (kind: string) => candidate.matches.filter((m) => m.basis === kind).length
      const coverage = coverageOf(candidate, result.items)
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
        candidate.roleContext.basis,
        candidate.roleContext.note ?? candidate.roleContext.product ?? "",
        candidate.novelty,
        candidate.origins.join(CODE_SEPARATOR),
        coverage.confirmed,
        coverage.toClarify,
        evidenceOf(candidate, result.items),
        result.createdAt,
      ]
    })
}
