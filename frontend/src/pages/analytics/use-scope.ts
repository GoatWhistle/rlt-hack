import { useQueryClient } from "@tanstack/react-query"
import { useCallback } from "react"
import { useSearchParams } from "react-router"
import type { AnalyticsFilters } from "@/entities/analytics/model"
import { readFilters, writeFilters } from "@/entities/analytics/scope"

export function useScope() {
  const [params, setParams] = useSearchParams()
  const client = useQueryClient()
  const filters = readFilters(params)
  const change = useCallback(
    (next: AnalyticsFilters) => setParams(new URLSearchParams(writeFilters(next))),
    [setParams],
  )
  const refresh = useCallback(
    () => client.invalidateQueries({ queryKey: ["analytics"] }),
    [client],
  )
  return { filters, params, search: writeFilters(filters), change, refresh }
}
