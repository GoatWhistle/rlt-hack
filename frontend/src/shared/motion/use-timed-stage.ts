import { useEffect, useState } from "react"

export type TimedStage<K extends string> = { readonly key: K; readonly at: number }

export function useTimedStage<K extends string>(
  stages: readonly TimedStage<K>[],
  pending: boolean,
): K | null {
  const [stage, setStage] = useState<K | null>(null)

  useEffect(() => {
    const [first, ...rest] = stages
    if (!pending || !first) {
      setStage(null)
      return
    }
    setStage(first.key)
    const timers = rest.map(({ key, at }) => window.setTimeout(() => setStage(key), at))
    return () => {
      for (const timer of timers) window.clearTimeout(timer)
    }
  }, [pending, stages])

  return stage
}
