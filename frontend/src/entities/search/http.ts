import type { HttpClient } from "@/shared/api/http-client"
import type { SearchGateway } from "./gateway"
import { parseRecentSearches, parseSearchResult } from "./parse"

export const SEARCHES_PATH = "/searches"

export function createHttpSearchGateway(client: HttpClient): SearchGateway {
  return {
    demo: false,
    search: (request) =>
      client.post(SEARCHES_PATH, { body: request, parse: parseSearchResult }),
    get: (searchId) =>
      client.get(`${SEARCHES_PATH}/${encodeURIComponent(searchId)}`, {
        parse: parseSearchResult,
      }),
    recent: (limit) =>
      client.get(SEARCHES_PATH, { query: { limit }, parse: parseRecentSearches }),
  }
}
