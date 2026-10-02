import type { OfferView } from "@/entities/evidence/model"
import type { CandidateView, ItemView, MatchView } from "@/entities/evidence/view"
import type { Candidate, CandidateMatch, QueryItem } from "./model"

export type OfferIndex = Readonly<Record<string, OfferView>>

function matchView(match: CandidateMatch, offers: OfferIndex): MatchView {
  const offer = match.offerId ? offers[match.offerId] : undefined
  return offer ? { ...match, offer } : match
}

export function candidateView(candidate: Candidate, offers: OfferIndex = {}): CandidateView {
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
    matches: candidate.matches.map((match) => matchView(match, offers)),
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
