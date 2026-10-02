import { useState } from "react"
import { localJson } from "@/shared/storage/local-json"

export const RECENT_OPEN_KEY = "lotive.search.recentOpen"

export function useRecentOpen() {
  const [open, setOpen] = useState(() => localJson.read(RECENT_OPEN_KEY) !== false)
  const change = (next: boolean) => {
    setOpen(next)
    localJson.write(RECENT_OPEN_KEY, next)
  }
  return [open, change] as const
}
