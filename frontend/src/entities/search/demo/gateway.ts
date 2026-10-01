import { ApiError } from "@/shared/api/api-error"
import { currentLocale } from "@/shared/i18n/i18n"
import type { Locale } from "@/shared/i18n/locale"
import { invalidQuery, type SearchGateway, searchNotFound } from "../gateway"
import { MAX_QUERY_LENGTH, summaryOf } from "../model"
import { parseSearchResult } from "../parse"
import { demoPayload, pickScenario, type StoredSearch } from "./catalog"
import { createSearchStore, type SearchStore } from "./store"

export const SEARCH_DELAY_MS = 700
export const READ_DELAY_MS = 150

const LETTER = /\p{L}/u

export type DemoSearchOptions = {
  readonly store?: SearchStore
  readonly now?: () => number
  readonly newId?: () => string
  readonly locale?: () => Locale
  readonly wait?: (ms: number) => Promise<void>
}

function pause(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

function validText(text: string): string {
  const trimmed = text.trim()
  if (!trimmed) throw invalidQuery("empty_query")
  if (trimmed.length > MAX_QUERY_LENGTH) throw invalidQuery("query_too_long")
  if (!LETTER.test(trimmed)) throw new ApiError({ status: 422, code: "query_not_understood" })
  return trimmed
}

export function createDemoSearchGateway(options: DemoSearchOptions = {}): SearchGateway {
  const store = options.store ?? createSearchStore()
  const now = options.now ?? Date.now
  const newId = options.newId ?? (() => crypto.randomUUID())
  const locale = options.locale ?? currentLocale
  const wait = options.wait ?? pause
  const build = (stored: StoredSearch) => parseSearchResult(demoPayload(stored, locale()))

  return {
    demo: true,
    search: async (request) => {
      await wait(SEARCH_DELAY_MS)
      const text = validText(request.text)
      const stored: StoredSearch = {
        searchId: newId(),
        text,
        scenario: pickScenario(text),
        createdAt: new Date(now()).toISOString(),
      }
      store.add(stored)
      return build(stored)
    },
    get: async (searchId) => {
      await wait(READ_DELAY_MS)
      const stored = store.find(searchId)
      if (!stored) throw searchNotFound()
      return build(stored)
    },
    recent: async (limit) => {
      await wait(READ_DELAY_MS)
      return store
        .all()
        .slice(0, limit)
        .map((stored) => summaryOf(build(stored)))
    },
  }
}
