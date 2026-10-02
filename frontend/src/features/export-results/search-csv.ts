import type { SearchResult } from "@/entities/search/model"
import { type CsvLabels, toCsv } from "./csv"
import { candidateRows, SEARCH_COLUMNS } from "./search-rows"

export { SEARCH_COLUMNS } from "./search-rows"

export function searchCsv(
  result: SearchResult,
  labels: CsvLabels,
  chosen?: readonly string[],
): string {
  return toCsv(SEARCH_COLUMNS, candidateRows(result, labels, chosen))
}

export function searchFileName(searchId: string): string {
  return `search-${searchId.replace(/[^\w-]+/g, "-")}-suppliers.csv`
}
