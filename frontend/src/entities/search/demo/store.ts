import { type JsonStorage, localJson } from "@/shared/storage/local-json"
import type { StoredSearch } from "./catalog"

export const SEARCHES_KEY = "rlt.searches.v1"
export const STORED_SEARCHES = 30

export type SearchStore = {
  readonly all: () => readonly StoredSearch[]
  readonly find: (searchId: string) => StoredSearch | undefined
  readonly add: (search: StoredSearch) => void
}

function isStoredSearch(value: unknown): value is StoredSearch {
  if (typeof value !== "object" || value === null) return false
  const entry = value as Record<string, unknown>
  return (
    typeof entry.searchId === "string" &&
    typeof entry.text === "string" &&
    (typeof entry.scenario === "string" || entry.scenario === null) &&
    typeof entry.createdAt === "string"
  )
}

export function createSearchStore(storage: JsonStorage = localJson): SearchStore {
  const saved = storage.read(SEARCHES_KEY)
  let searches: StoredSearch[] = Array.isArray(saved) ? saved.filter(isStoredSearch) : []
  return {
    all: () => searches,
    find: (searchId) => searches.find((search) => search.searchId === searchId),
    add: (search) => {
      searches = [search, ...searches].slice(0, STORED_SEARCHES)
      storage.write(SEARCHES_KEY, searches)
    },
  }
}
