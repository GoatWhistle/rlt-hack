import { ApiError } from "@/shared/api/api-error"
import type { SearchHistoryPage, SearchRequest, SearchResult, SearchSummary } from "./model"

export type SearchGateway = {
  readonly search: (request: SearchRequest) => Promise<SearchResult>
  readonly get: (searchId: string) => Promise<SearchResult>
  readonly recent: (limit: number) => Promise<readonly SearchSummary[]>
  readonly history: (limit: number, before?: string) => Promise<SearchHistoryPage>
}

export function invalidQuery(code: "empty_query" | "query_too_long"): ApiError {
  return new ApiError({ status: 422, code })
}
