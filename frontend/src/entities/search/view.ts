import type { CandidateView, ItemView } from "@/entities/evidence/view"
import type { Candidate, QueryItem } from "./model"

export function candidateView(candidate: Candidate): CandidateView {
  return {
    id: candidate.id,
    rank: candidate.rank,
    name: candidate.name,
    inn: candidate.inn,
    role: candidate.role,
    roleSource: candidate.roleSource,
    region: candidate.region || undefined,
    contacts: candidate.contacts,
    status: candidate.status,
    checkReasons: candidate.checkReasons,
    highlights: candidate.highlights,
    matches: candidate.matches,
    similarPurchases: candidate.history.similarPurchases,
    wins: candidate.history.wins,
    purchases: candidate.history.records.map((record) => ({
      key: record.lotId,
      lotId: record.lotId,
      title: record.title,
      outcome: record.outcome,
      itemIds: record.itemIds,
    })),
  }
}

export function itemViews(items: readonly QueryItem[]): ItemView[] {
  return items.map((item) => ({ id: item.id, name: item.name }))
}
