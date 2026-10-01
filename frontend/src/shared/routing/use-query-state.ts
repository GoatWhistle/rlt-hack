import { useState } from "react"
import { useSearchParams } from "react-router"

export type QueryState<K extends string> = Readonly<Record<K, string | null>>
export type QueryChange<K extends string> = Partial<Record<K, string | null>>

function read<K extends string>(params: URLSearchParams, keys: readonly K[]): QueryState<K> {
  return Object.fromEntries(keys.map((key) => [key, params.get(key)])) as QueryState<K>
}

function signature<K extends string>(state: QueryState<K>, keys: readonly K[]): string {
  return keys.map((key) => `${key}=${state[key] ?? ""}`).join("&")
}

export function useQueryState<K extends string>(
  keys: readonly K[],
): readonly [QueryState<K>, (change: QueryChange<K>) => void] {
  const [params, setParams] = useSearchParams()
  const fromUrl = read(params, keys)
  const [state, setState] = useState(fromUrl)
  const [seen, setSeen] = useState(() => signature(fromUrl, keys))
  const current = signature(fromUrl, keys)
  if (current !== seen) {
    setSeen(current)
    setState(fromUrl)
  }

  function update(change: QueryChange<K>) {
    const next = { ...state, ...change } as QueryState<K>
    setState(next)
    setParams(
      (previous) => {
        const written = new URLSearchParams(previous)
        for (const key of keys) {
          const value = next[key]
          if (value) written.set(key, value)
          else written.delete(key)
        }
        return written
      },
      { replace: true, preventScrollReset: true },
    )
  }

  return [state, update] as const
}
