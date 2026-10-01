import type { AnimationEvent } from "react"
import { useCallback, useEffect, useState } from "react"

export type PresenceState = "open" | "closed"

export const EXIT_FALLBACK_MS = 400

export type Presence = {
  readonly isMounted: boolean
  readonly state: PresenceState
  readonly onAnimationEnd: (event: AnimationEvent<Element>) => void
}

export function usePresence(open: boolean, fallbackMs = EXIT_FALLBACK_MS): Presence {
  const [isMounted, setMounted] = useState(open)
  if (open && !isMounted) setMounted(true)

  useEffect(() => {
    if (open || !isMounted) return
    const timer = window.setTimeout(() => setMounted(false), fallbackMs)
    return () => window.clearTimeout(timer)
  }, [open, isMounted, fallbackMs])

  const onAnimationEnd = useCallback(
    (event: AnimationEvent<Element>) => {
      if (!open && event.target === event.currentTarget) setMounted(false)
    },
    [open],
  )

  return { isMounted: open || isMounted, state: open ? "open" : "closed", onAnimationEnd }
}
