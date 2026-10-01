import type { Locale } from "@/shared/i18n/locale"
import { DEFAULT_LIMIT } from "../model"
import { fallbackItems } from "./fallback"
import groats from "./groats.json"
import groatsCheck from "./groats-check.json"
import { type Loose, localize, omit, records } from "./localize"
import medical from "./medical.json"
import office from "./office.json"

export const DEMO_PIPELINE = { version: "demo-v1", channels: ["lexical", "history"] } as const

export type DemoScenario = {
  readonly id: string
  readonly keywords: readonly string[]
  readonly warnings: readonly unknown[]
  readonly items: readonly unknown[]
  readonly candidates: readonly unknown[]
}

export const SCENARIOS: readonly DemoScenario[] = [
  { ...groats, candidates: [...groats.candidates, ...groatsCheck] },
  office,
  medical,
]

export type StoredSearch = {
  readonly searchId: string
  readonly text: string
  readonly scenario: string | null
  readonly createdAt: string
}

export function pickScenario(text: string): string | null {
  const needle = text.toLowerCase()
  let best: { id: string; hits: number } | null = null
  for (const scenario of SCENARIOS) {
    const hits = scenario.keywords.filter((keyword) => needle.includes(keyword)).length
    if (hits > 0 && hits > (best?.hits ?? 0)) best = { id: scenario.id, hits }
  }
  return best?.id ?? null
}

function candidatePayload(candidate: unknown, index: number): Loose {
  const fields = omit(candidate, ["kpps", "identity"])
  const rank = index + 1
  return {
    ...fields,
    rank,
    matches: records(fields.matches).map((match) => omit(match, ["offer"])),
    score: { ...omit(fields.score, []), channels: [{ channel: "lexical", rank }] },
  }
}

export function demoPayload(stored: StoredSearch, locale: Locale): unknown {
  const scenario = SCENARIOS.find((entry) => entry.id === stored.scenario)
  return localize(
    {
      searchId: stored.searchId,
      query: { text: stored.text, locale, limit: DEFAULT_LIMIT, filters: {} },
      items: scenario ? scenario.items : fallbackItems(stored.text),
      candidates: scenario ? scenario.candidates.map(candidatePayload) : [],
      pipeline: { ...DEMO_PIPELINE, asOf: stored.createdAt },
      warnings: scenario?.warnings ?? [],
      createdAt: stored.createdAt,
    },
    locale,
  )
}

function findCandidate(supplierId: string): Loose | undefined {
  return SCENARIOS.flatMap((scenario) => records(scenario.candidates)).find(
    (candidate) => candidate.id === supplierId,
  )
}

function offerPayload(match: Loose): Loose[] {
  const offer = omit(match.offer, [])
  if (!match.offer) return []
  return [{ ...offer, id: match.offerId, currency: "RUB", source: match.source }]
}

export function demoProfilePayload(supplierId: string, locale: Locale): unknown {
  const candidate = findCandidate(supplierId)
  if (!candidate) return undefined
  return localize(
    {
      id: candidate.id,
      name: candidate.name,
      inn: candidate.inn,
      kpps: candidate.kpps,
      region: candidate.region,
      identity: candidate.identity,
      role: candidate.role,
      roleSource: candidate.roleSource,
      contacts: { site: "", email: "", phone: "", ...omit(candidate.contacts, []) },
      offers: records(candidate.matches).flatMap(offerPayload),
    },
    locale,
  )
}
