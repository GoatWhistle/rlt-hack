import { useCallback } from "react"
import { useSearchParams } from "react-router"

export type QueryState<K extends string> = Readonly<Record<K, string | null>>
export type QueryChange<K extends string> = Partial<Record<K, string | null>>

export function useQueryState<K extends string>(
  keys: readonly K[],
): readonly [QueryState<K>, (change: QueryChange<K>) => void] {
  const [params, setParams] = useSearchParams()
  const state = Object.fromEntries(keys.map((key) => [key, params.get(key)])) as QueryState<K>
  const update = useCallback(
    (change: QueryChange<K>) => {
      setParams(
        (current) => {
          const next = new URLSearchParams(current)
          for (const [key, value] of Object.entries<string | null | undefined>(change)) {
            if (value) next.set(key, value)
            else next.delete(key)
          }
          return next
        },
        { replace: true, preventScrollReset: true },
      )
    },
    [setParams],
  )
  return [state, update] as const
}
