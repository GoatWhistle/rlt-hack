import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { keptAcrossLocales } from "@/shared/api/locale-keys"
import type { Locale } from "@/shared/i18n/locale"
import { useLocale } from "@/shared/i18n/locale-provider"
import { useSearchGateway } from "./gateway-context"
import { HISTORY_PAGE, RECENT_LIMIT, type SearchHistoryPage, type SearchRequest } from "./model"

const RECENT_PART = "recent"

export const searchKeys = {
  all: ["searches"] as const,
  detail: (locale: Locale, searchId: string) =>
    ["searches", locale, "detail", searchId] as const,
  recent: (locale: Locale, limit: number) => ["searches", locale, RECENT_PART, limit] as const,
  history: (locale: Locale) => ["searches", locale, RECENT_PART, "history"] as const,
}

export function useSearchResult(searchId: string) {
  const gateway = useSearchGateway()
  const { locale } = useLocale()
  const key = searchKeys.detail(locale, searchId)
  return useQuery({
    queryKey: key,
    queryFn: () => gateway.get(searchId),
    placeholderData: keptAcrossLocales(key),
  })
}

export function useRecentSearches(limit = RECENT_LIMIT) {
  const gateway = useSearchGateway()
  const { locale } = useLocale()
  const key = searchKeys.recent(locale, limit)
  return useQuery({
    queryKey: key,
    queryFn: () => gateway.recent(limit),
    placeholderData: keptAcrossLocales(key),
    staleTime: 0,
  })
}

function nextCursor(page: SearchHistoryPage): string | undefined {
  return page.hasMore ? page.searches.at(-1)?.searchId : undefined
}

export function useSearchHistory() {
  const gateway = useSearchGateway()
  const { locale } = useLocale()
  return useInfiniteQuery({
    queryKey: searchKeys.history(locale),
    queryFn: ({ pageParam }) => gateway.history(HISTORY_PAGE, pageParam),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: nextCursor,
    staleTime: 0,
  })
}

export function useRunSearch() {
  const gateway = useSearchGateway()
  const client = useQueryClient()
  const { locale } = useLocale()
  return useMutation({
    mutationFn: (request: SearchRequest) => gateway.search(request),
    meta: { silent: true },
    onSuccess: (result) => {
      client.setQueryData(searchKeys.detail(locale, result.searchId), result)
      void client.invalidateQueries({
        queryKey: searchKeys.all,
        predicate: (query) => query.queryKey[2] === RECENT_PART,
        refetchType: "none",
      })
    },
  })
}
