import { useQuery } from "@tanstack/react-query"
import { keptAcrossLocales } from "@/shared/api/locale-keys"
import type { Locale } from "@/shared/i18n/locale"
import { useLocale } from "@/shared/i18n/locale-provider"
import { useAnalyticsGateway } from "./gateway-context"
import type { AnalyticsFilters, RecordsQuery } from "./model"

export const REFRESH_MS = 60_000

export const analyticsKeys = {
  overview: (locale: Locale, filters: AnalyticsFilters) =>
    ["analytics", locale, "overview", filters] as const,
  categories: (locale: Locale, filters: AnalyticsFilters) =>
    ["analytics", locale, "categories", filters] as const,
  quality: (locale: Locale, filters: AnalyticsFilters) =>
    ["analytics", locale, "quality", filters] as const,
  sources: (locale: Locale, filters: AnalyticsFilters) =>
    ["analytics", locale, "sources", filters] as const,
  records: (locale: Locale, filters: AnalyticsFilters, query: RecordsQuery) =>
    ["analytics", locale, "records", filters, query] as const,
}

const live = { refetchInterval: REFRESH_MS, refetchIntervalInBackground: false } as const

export function useOverview(filters: AnalyticsFilters) {
  const gateway = useAnalyticsGateway()
  const { locale } = useLocale()
  const key = analyticsKeys.overview(locale, filters)
  return useQuery({
    queryKey: key,
    queryFn: () => gateway.overview(filters),
    placeholderData: keptAcrossLocales(key),
    ...live,
  })
}

export function useCategories(filters: AnalyticsFilters) {
  const gateway = useAnalyticsGateway()
  const { locale } = useLocale()
  const key = analyticsKeys.categories(locale, filters)
  return useQuery({
    queryKey: key,
    queryFn: () => gateway.categories(filters),
    placeholderData: keptAcrossLocales(key),
    ...live,
  })
}

export function useQuality(filters: AnalyticsFilters) {
  const gateway = useAnalyticsGateway()
  const { locale } = useLocale()
  const key = analyticsKeys.quality(locale, filters)
  return useQuery({
    queryKey: key,
    queryFn: () => gateway.quality(filters),
    placeholderData: keptAcrossLocales(key),
    ...live,
  })
}

export function useSources(filters: AnalyticsFilters) {
  const gateway = useAnalyticsGateway()
  const { locale } = useLocale()
  const key = analyticsKeys.sources(locale, filters)
  return useQuery({
    queryKey: key,
    queryFn: () => gateway.sources(filters),
    placeholderData: keptAcrossLocales(key),
    ...live,
  })
}

export function useRecords(filters: AnalyticsFilters, query: RecordsQuery) {
  const gateway = useAnalyticsGateway()
  const { locale } = useLocale()
  const key = analyticsKeys.records(locale, filters, query)
  return useQuery({
    queryKey: key,
    queryFn: () => gateway.records(filters, query),
    placeholderData: keptAcrossLocales(key),
  })
}
