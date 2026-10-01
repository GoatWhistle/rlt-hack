import { useCallback, useSyncExternalStore } from "react"
import { localJson } from "@/shared/storage/local-json"

export const SHORTLIST_KEY = "rlt.shortlist.v1"
export const SEARCH_SCOPE = "~search"

export type LotShortlists = Readonly<Record<string, readonly string[]>>
type Shortlists = Readonly<Record<string, LotShortlists>>

const EMPTY: readonly string[] = []
const NONE: LotShortlists = {}
const listeners = new Set<() => void>()
let cache: Shortlists | undefined

function load(): Shortlists {
  if (cache) return cache
  const saved = localJson.read(SHORTLIST_KEY)
  cache = typeof saved === "object" && saved !== null ? (saved as Shortlists) : {}
  return cache
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener)
  return () => listeners.delete(listener)
}

export function resetShortlists(): void {
  cache = undefined
  for (const listener of listeners) listener()
}

export function shortlistsOf(uploadId: string): LotShortlists {
  return load()[uploadId] ?? NONE
}

export function toggleShortlisted(uploadId: string, lotId: string, companyId: string): void {
  const current = shortlistsOf(uploadId)[lotId] ?? EMPTY
  const next = current.includes(companyId)
    ? current.filter((id) => id !== companyId)
    : [...current, companyId]
  cache = { ...load(), [uploadId]: { ...shortlistsOf(uploadId), [lotId]: next } }
  localJson.write(SHORTLIST_KEY, cache)
  for (const listener of listeners) listener()
}

export function useShortlist(uploadId: string, lotId: string) {
  const ids = useSyncExternalStore(
    subscribe,
    () => shortlistsOf(uploadId)[lotId] ?? EMPTY,
    () => EMPTY,
  )
  const toggle = useCallback(
    (companyId: string) => toggleShortlisted(uploadId, lotId, companyId),
    [uploadId, lotId],
  )
  return { ids, toggle }
}

export function searchShortlistOf(searchId: string): readonly string[] {
  return shortlistsOf(SEARCH_SCOPE)[searchId] ?? EMPTY
}

export function useSearchShortlist(searchId: string) {
  return useShortlist(SEARCH_SCOPE, searchId)
}
