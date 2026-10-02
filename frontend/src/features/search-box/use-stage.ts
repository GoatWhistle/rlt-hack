import { useTimedStage } from "@/shared/motion/use-timed-stage"

export const SEARCH_STAGES = [
  { key: "parse", at: 0 },
  { key: "companies", at: 800 },
  { key: "evidence", at: 2000 },
  { key: "slow", at: 6000 },
] as const

export type SearchStage = (typeof SEARCH_STAGES)[number]["key"]

export function useStage(pending: boolean): SearchStage | null {
  return useTimedStage(SEARCH_STAGES, pending)
}
