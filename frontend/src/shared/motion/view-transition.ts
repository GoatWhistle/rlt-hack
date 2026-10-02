import { flushSync } from "react-dom"
import { prefersReducedMotion } from "./settle-delay"

export function withViewTransition(mode: string, change: () => void): void {
  if (!("startViewTransition" in document) || prefersReducedMotion()) {
    change()
    return
  }
  const root = document.documentElement
  root.dataset.transition = mode
  const transition = document.startViewTransition(() => flushSync(change))
  void transition.finished.finally(() => {
    if (root.dataset.transition === mode) delete root.dataset.transition
  })
}
