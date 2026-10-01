import { useEffect, useState } from "react"

export const SEARCH_STAGES = [
  { key: "parse", at: 0 },
  { key: "companies", at: 800 },
  { key: "evidence", at: 2000 },
  { key: "slow", at: 6000 },
] as const

export type SearchStage = (typeof SEARCH_STAGES)[number]["key"]

export function useStage(pending: boolean): SearchStage | null {
  const [stage, setStage] = useState<SearchStage | null>(null)

  useEffect(() => {
    if (!pending) {
      setStage(null)
      return
    }
    setStage(SEARCH_STAGES[0].key)
    const timers = SEARCH_STAGES.slice(1).map(({ key, at }) =>
      window.setTimeout(() => setStage(key), at),
    )
    return () => {
      for (const timer of timers) window.clearTimeout(timer)
    }
  }, [pending])

  return stage
}
