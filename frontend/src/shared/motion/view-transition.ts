import { flushSync } from "react-dom"
import { prefersReducedMotion } from "./settle-delay"

export const TRANSITION_LIMIT_MS = 900

export function withViewTransition(mode: string, change: () => void): void {
  if (!("startViewTransition" in document) || prefersReducedMotion()) {
    change()
    return
  }
  const root = document.documentElement
  root.dataset.transition = mode
  const transition = document.startViewTransition(() => flushSync(change))
  const limit = window.setTimeout(() => transition.skipTransition(), TRANSITION_LIMIT_MS)
  transition.ready.catch(() => undefined)
  void transition.finished.finally(() => {
    window.clearTimeout(limit)
    if (root.dataset.transition === mode) delete root.dataset.transition
  })
}
