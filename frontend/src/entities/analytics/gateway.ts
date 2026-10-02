import type { HttpClient } from "@/shared/api/http-client"
import type {
  AnalyticsFilters,
  CategoriesReport,
  Overview,
  QualityReport,
  RecordsPage,
  RecordsQuery,
  SourcesReport,
} from "./model"
import {
  parseCategories,
  parseOverview,
  parseQuality,
  parseRecords,
  parseRuns,
  parseSources,
} from "./parse-report"

export const ANALYTICS_API_PATH = "/analytics"

export type AnalyticsGateway = {
  readonly overview: (filters: AnalyticsFilters) => Promise<Overview>
  readonly categories: (filters: AnalyticsFilters) => Promise<CategoriesReport>
  readonly quality: (filters: AnalyticsFilters) => Promise<QualityReport>
  readonly sources: (filters: AnalyticsFilters) => Promise<SourcesReport>
  readonly records: (filters: AnalyticsFilters, query: RecordsQuery) => Promise<RecordsPage>
}

function scope(filters: AnalyticsFilters) {
  return {
    sourceId: filters.sourceId,
    sourceType: filters.sourceType,
    region: filters.region,
  }
}

export function createHttpAnalyticsGateway(client: HttpClient): AnalyticsGateway {
  const get = <T>(name: string, filters: AnalyticsFilters, parse: (data: unknown) => T) =>
    client.get(`${ANALYTICS_API_PATH}/${name}`, { query: scope(filters), parse })
  return {
    overview: (filters) => get("overview", filters, parseOverview),
    categories: (filters) => get("categories", filters, parseCategories),
    quality: (filters) => get("quality", filters, parseQuality),
    sources: async (filters) => {
      const [sources, runs] = await Promise.all([
        get("sources", filters, parseSources),
        get("runs", filters, parseRuns),
      ])
      return {
        meta: sources.meta,
        items: sources.items,
        runs: runs.items,
        success: runs.success,
        partial: runs.partial,
      }
    },
    records: (filters, query) =>
      client.get(`${ANALYTICS_API_PATH}/records`, {
        query: {
          ...scope(filters),
          category: query.category,
          problem: query.problem,
          limit: query.limit,
          offset: query.offset,
        },
        parse: parseRecords,
      }),
  }
}
